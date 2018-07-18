"""
    Class to interface with a redash server
"""
import click
import requests
from ruamel import yaml


class Redash:
    """
        Class to upload/download queries from redash 
    """

    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key

    def Get_Queries(self, dontfilter=False):
        """
            Get all queries from the given redash server
            It does so in bulk queries. But it doesn't get the visualizations
            In case that you don't want to get extra contents from the queries to be filtered
            you can pass the dontfilter param.
        """
        queries = []
        headers = {'Authorization': 'Key {}'.format(self.api_key)}
        path = "{}/api/queries".format(self.url)
        has_more = True
        page = 1
        while has_more:
            response = requests.get(path, headers=headers, params={'page': page}).json()
            queries.extend(response['results'])
            has_more = page * response['page_size'] + 1 <= response['count']
            page += 1

        if not dontfilter:
            queries = self.filter_fields_query_list(queries)
        return queries

    def Get_Full_Queries(self, queries):
        """
            Download the query and its visualizations.
            If you download the queries in bulk, they don't contain the visualizations
            This call needs to first Get_Queries and then do one request per query to the
            server to get the visualizations
        """

        headers = {'Authorization': 'Key {}'.format(self.api_key)}
        path = "{}/api/queries".format(self.url)
        full_queries = []
        for query in queries:
            response = requests.get(path + '/' + str(query['id']), headers=headers).json()
            full_query = self.filter_fields_query(response)
            full_queries.append(full_query)
        return full_queries

    def Put_Queries(self, old_queries, new_queries):
        """
            Upload the queries to the given redash server
            If it has visualizations it will put them also
            It uses the field (hack) `redpush_id` to find the query in redash server
            and update it if there. If the query being uploaded doesn't have that property
            it will not be uploaded.
            The new queries list is modified on the process. So don't rely on it afterwards
        """
        headers = {'Authorization': 'Key {}'.format(self.api_key)}
        path = "{}/api/queries".format(self.url)

        # we get dashboards before, as an optimization. Before we were doing it on each widget, but it is
        # very expensive, so we move it out, and pass it to the chain down. We save lots of extra calls to
        # the server making it so much faster to run
        dash_list = self.Get_Dashboards()

        for query in new_queries:
            if 'redpush_id' not in query:
                print('Query without tracking id, ignored')
                continue

            redpush_id = query['redpush_id']
            query.pop('redpush_id', None)

            old_query = self.find_by_redpush_id(old_queries, redpush_id)
            # print(old_query)
            extra_path = ''
            if old_query != None:
                # we are updating the query
                id = old_query['id']
                print('updating query ' + str(id), flush=True)
                extra_path = '/' + str(id)
            else:
                print('creating new query ' + query['name'], flush=True)

            if 'options' not in query:
                query['options'] = {}
            query['options']['redpush_id'] = redpush_id
            query['is_draft'] = False
            query['is_archived'] = False
            if 'visualizations' in query:
                visualizations = query['visualizations']
                # visualizations need to be uploaded in a diff call
                query['visualizations'] = None

            response = requests.post(path + extra_path, headers=headers, json=query).json()
            id = response['id']
            # Now we handle the visualization
            if visualizations != None:
                for visualization in visualizations:
                    visualization['query_id'] = id

                    # we might have received a new copy of the dashboards from the server
                    dash_list = self.Put_Visualization(visualization, old_query, dash_list)
            # print(response)

    def Archive_Missing_Queries(self, server_queries, new_queries):
        """
            Make a diff between server_queries and the new_queries,
            the ones appearing in server_queries but not in new_queries
            are archived.
        """
        headers = {'Authorization': 'Key {}'.format(self.api_key)}
        path = "{}/api/queries".format(self.url)

        for query in server_queries:

            deleteQuery = False
            if 'options' in query:
                if 'redpush_id' in query['options']:
                    redpush_id = query['options']['redpush_id']
                    new_query = self.find_by_redpush_id(new_queries, redpush_id)
                    deleteQuery = new_query == None

                else:
                    deleteQuery = True
                    print('Query without tracking id, deleting…', flush=True)
                    # if query doesn't have redpush_id we will get rid of it

            else:
                    deleteQuery = True
                    print('Query without tracking id, deleting…', flush=True)
                    # if query doesn't have redpush_id we will get rid of it

            if deleteQuery:
                # the server query isn't in the file, so we archive it
                id = query['id']
                print('deleting query ' + str(id), flush=True)
                extra_path = '/' + str(id)
                response = requests.delete(path + extra_path, headers=headers, json=query).json()
                # if response.status_code != 200:
                # print('error deleting query', response)

    def Put_Visualization(self, visualization, old_query, dash_list):
        """
            Upload the visualizations to the given redash server
            If it has visualizations it will put them also
            It uses the field (hack) `redpush_id` to find the query in redash server
            and update it if there. If the query being uploaded doesn't have that property
            it will not be uploaded.
            If a visualization has also the `redpush_dashboard` it will be added to that dashboard
            (if not there already)
            It needs also the old query if already there, so we update the visuals and
            not create duplicates

            It returns the dash_list, which might or might not be the same we received. If nothing was 
            added then it is the same, otherwise it was refreshed from the server and we have new contents
        """

        if 'redpush_id' not in visualization:
            print('Visualization without tracking id, ignored')
            return

        headers = {'Authorization': 'Key {}'.format(self.api_key)}
        path = "{}/api/visualizations".format(self.url)

        # redash doesn't allow our extra properties, so remove them
        redpush_id = visualization['redpush_id']
        del visualization['redpush_id']

        redpush_dashboards = []
        if 'redpush_dashboards' in visualization:
            redpush_dashboards = visualization['redpush_dashboards']
            del visualization['redpush_dashboards']

        extra_path = ''

        if old_query != None:
            # we are updating so we need to find the id first
            filtered = list(filter(lambda x: 'redpush_id' in x and x['redpush_id'] == redpush_id, old_query['visualizations']))
            if filtered:
                if len(filtered) > 1:
                    print('There are repeated visuals. Using the first')
                old_id = filtered[0]['id']
                extra_path = '/{}'.format(old_id)

        if 'options' not in visualization:
            visualization['options'] = {}
        visualization['options']['redpush_id'] = redpush_id
        response = requests.post(path + extra_path, headers=headers, json=visualization).json()
        visual_id = response['id']  # the id we got from the just added visual

        # if there is redpush_dashboard then lets check if we need to add to dashboard
        if redpush_dashboards:
            for widget_properties in redpush_dashboards:
                # check if that dashboard is already in server, and if not create it
                # check against name, as if deleted it would get a new slug
                filtered_dash_list = list(filter(lambda x: x['name'] == widget_properties['name'], dash_list))
                if filtered_dash_list:
                    if len(filtered_dash_list) > 1:
                        print('More than one dashboard with the same id, error!!!')
                    dash = filtered_dash_list[0]
                else:
                    print('Creating dashboard: ', widget_properties['name'])

                    dash = self.Create_Dashboard(widget_properties['name'])
                    dash_list = self.Get_Dashboards()

                # check if visual already in dashboard, and if not add it
                need_to_add_widget = False
                if 'widgets' in dash and dash['widgets']:
                    #find the widget if already there
                    filtered_widget_list = list(filter(lambda x: 'visualization' in x and x['visualization']['id'] == visual_id, dash['widgets']))
                    if not filtered_widget_list:
                        need_to_add_widget = True
                else:
                    need_to_add_widget = True

                # as we have the visualization from file, we need to put the id
                visualization['id'] = visual_id
                row = 0
                col = 0
                if 'row' in widget_properties and widget_properties['row'] > 0:
                    row = widget_properties['row']
                if 'col' in widget_properties and widget_properties['col'] > 0:
                    col = widget_properties['col']
                if need_to_add_widget:
                    self.Create_Widget(dash['id'], visualization, widget_properties)
                else:
                    first = filtered_widget_list[0]
                    self.Update_Widget(dash['id'], first['id'], widget_properties)

        return dash_list  # In case we have refreshed it when adding a new one

    def Create_Widget(self, dashboard_id, visual, widget_properties):
        """
            Create a widget into a dashboard
        """
        headers = {'Authorization': 'Key {}'.format(self.api_key)}
        path = "{}/api/widgets".format(self.url)

        position = self.get_Widget_position(widget_properties)

        widget = {
            'visualization': visual,
            'dashboard_id': dashboard_id,
            'visualization_id': visual['id'],
            'options': {'position': position},
            'width': 1
        }

        response = requests.post(path, headers=headers, json=widget).json()

    def get_Widget_position(self, widget_properties):
        """
            From the properties of a visualization in the yaml, we generate the position properties
            that redash expects on the API
        """
        size = "medium"
        if 'size' in widget_properties and len(widget_properties['size']) > 0:
            size = widget_properties['size']
        col = 0
        if 'col' in widget_properties and widget_properties['col'] > 0:
            col = widget_properties['col']
        row = 0
        if 'row' in widget_properties and widget_properties['row'] > 0:
            row = widget_properties['row']

        multiplierDef = {
            'small': 2,
            'medium': 3,
            'large': 1
        }

        sizeXDef = {    # defining how big in X the widgets are
            'small': 2,
            'medium': 3,
            'large': 6  # max size in redash
        }

        sizeYDef = {    # defining how big in X the widgets are
            'small': 5,
            'medium': 9,
            'large': 12
        }
        multiplier = multiplierDef[size]

        position = {
            'autoHeight': False,
            'row': row,
            'col': col * multiplier,
            'sizeX': sizeXDef[size],
            'sizeY': sizeYDef[size],
        }
        return position

    def Update_Widget(self, dashboard_id, widget_id, widget_properties):
        """
            Update a widget already in a dashboard
        """
        headers = {'Authorization': 'Key {}'.format(self.api_key)}
        path = "{}/api/widgets/{}".format(self.url, widget_id)

        position = self.get_Widget_position(widget_properties)

        widget = {
            'dashboard_id': dashboard_id,
            'options': {'position': position},
            'text': '',
            'width': 1
        }
        response = requests.post(path, headers=headers, json=widget).json()

    def Get_Dashboards(self):
        """
            Get all dashboards from the given redash server
            For that it needs to first get the list and then get the details of each one

        """
        headers = {'Authorization': 'Key {}'.format(self.api_key)}
        path = "{}/api/dashboards".format(self.url)
        dash_id_list = requests.get(path, headers=headers).json()

        path_id_template = "{}/api/dashboards/{}"
        dashboards = []
        # now we get the details
        for dash_id in dash_id_list:
            slug = dash_id['slug']
            path_id = path_id_template.format(self.url, slug)
            dashboard = requests.get(path_id, headers=headers).json()

            # we need to filter some stuff, mostly inside the widgets
            dashboard = self.filter_fields_blacklist(dashboard, ['updated_at', 'created_at', 'is_archived', 'is_draft', 'version', 'layout', 'can_edit', 'user_id'])
            if 'widgets' in dashboard:
                filtered_widgets = []
                for widget in dashboard['widgets']:
                    filt_widget = self.filter_fields_blacklist(widget, ['updated_at', 'created_at', 'is_archived', 'is_draft', 'version'])
                    filtered_widgets.append(filt_widget)
                dashboard['widgets'] = filtered_widgets
            dashboards.append(dashboard)

        return dashboards

    def Create_Dashboard(self, name):
        """
            Create a dashboard using the name both for the name and slug (the part of the path at the end of the dashboard url)
            Warning, this function doesn't check if the dashboard with that name is already created, and if it is
            it will create a duplicate
        """
        headers = {'Authorization': 'Key {}'.format(self.api_key)}
        path = "{}/api/dashboards".format(self.url)

        dash = {'name': name}
        response = requests.post(path, headers=headers, json=dash).json()
        # as we want it published, we need a second request to update it
        response['is_draft'] = False
        update = self.filter_fields_blacklist(response, ['updated_at', 'created_at', 'version'])

        response = requests.post(path + '/' + str(response['id']), headers=headers, json=update).json()
        # This call returns an error but still makes the change :)
        return update

    def filter_fields_query(self, query):
        """
            Remove all unneeded fields of the query from redash.
            That means mostly the ones that cannot be sent when creating a new query
            it also does the hack of moving the redpush_id from the options to the top level of the query
        """
        new_query = {}
        for valid_key in ['name', 'description', 'query', 'id', 'data_source_id', 'options', 'visualizations']:
            if valid_key in query:
                if valid_key == 'visualizations':
                    # if there is a visualizations key, we need to do some cleanup also
                    new_query[valid_key] = list(map(lambda i: self.filter_fields_blacklist(i, ['created_at', 'updated_at']), query[valid_key]))
                    for visualization in new_query['visualizations']:
                        if 'options' in visualization and 'redpush_id' in visualization['options']:
                            redpush_id = visualization['options']['redpush_id']
                            del visualization['options']['redpush_id']
                            visualization['redpush_id'] = redpush_id
                elif valid_key == 'options':
                    # check if we have the redpush_id and if we do put it in the query
                    if 'redpush_id' in query['options']:
                        new_query['redpush_id'] = query['options']['redpush_id']
                    new_query[valid_key] = self.filter_fields_blacklist(query[valid_key], ['redpush_id'])  # we don't want our internal id there
                else:
                    new_query[valid_key] = query[valid_key]

        return new_query

    def filter_fields_query_list(self, queries):
        """
            Remove all unneeded fields of the query from redash.
            That means mostly the ones that cannot be sent when creating a new query
        """
        new_queries = []
        for query in queries:
            new_queries.append(self.filter_fields_query(query))
        return new_queries

    def filter_fields_blacklist(self, item, blacklist):
        """
            Remove all the fields not in the whitelist of the item
        """
        new_item = {}
        for key in item:
            if key not in blacklist:
                new_item[key] = item[key]

        return new_item

    def find_by_redpush_id(self, queries, redpush_id):
        """
            find a query in a list of queries that has the given redpush_id 
        """
        for query in queries:
            if 'redpush_id' in query:
                if query['redpush_id'] == redpush_id:
                    return query

    def Create_Users(self, users):
        """
            Tries to create in Redash a list of users. users is a list of dicts with `name` and `email`
            If the user is already created then it will silently fail
        """
        headers = {'Authorization': 'Key {}'.format(self.api_key)}
        path = "{}/api/users".format(self.url)

        for user in users:
            response = requests.post(path, headers=headers, json=user).json()
            print(response)
