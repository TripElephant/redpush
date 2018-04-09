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

    def Get_Queries(self):
        """
            Get all queries from the given redash server
            It does so in bulk queries. But it doesn't get the visualizations
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
        """
        headers = {'Authorization': 'Key {}'.format(self.api_key)}
        path = "{}/api/queries".format(self.url)
        for query in new_queries:
            if 'redpush_id' not in query:
                print('Query without tracking id, ignored')
                continue

            redpush_id = query['redpush_id']
            query.pop('redpush_id',None)

            old_query = self.find_by_redpush_id(old_queries, redpush_id)
            # print(old_query)
            extra_path = ''
            if old_query != None:
                # we are updating the query
                id = old_query['id']
                print('updating queery ' +str(id))
                extra_path = '/'+str(id)
            
            if 'options' not in query:
                query['options'] = {}
            query['options']['redpush_id'] = redpush_id
            query['is_draft'] = False
            query['is_archived'] = False
            if 'visualizations' in query:
                visualizations = query['visualizations']
                query['visualizations'] = None # visualizations need to be uploaded in a diff call
            response = requests.post(path + extra_path, headers=headers, json=query).json()
            
            id = response['id']
            # Now we handle the visualization
            if visualizations != None:
                for visualization in visualizations:
                    visualization['query_id'] = id
                    self.Put_Visualization(visualization)
            # print(response)


    def Put_Visualization(self, visualization):
        """
            Upload the visualizations to the given redash server
            If it has visualizations it will put them also
            It uses the field (hack) `redpush_id` to find the query in redash server
            and update it if there. If the query being uploaded doesn't have that property
            it will not be uploaded.
        """
        headers = {'Authorization': 'Key {}'.format(self.api_key)}
        path = "{}/api/visualizations".format(self.url)
        response = requests.post(path, headers=headers, json=visualization)
        # print(response)

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
            path_id = path_id_template.format(self.url,slug)
            dashboard = requests.get(path_id, headers=headers).json()
            dashboards.append(dashboard)

        return dashboards

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
                    new_query[valid_key] = list(map(lambda i: self.filter_fields_blacklist(i,['created_at', 'updated_at']), query[valid_key]))
                elif valid_key == 'options':
                    # check if we have the redpush_id and if we do put it in the query
                    # print([query['options']])
                    if 'redpush_id' in query['options']:
                        new_query['redpush_id'] = query['options']['redpush_id']
                    new_query[valid_key] = self.filter_fields_blacklist(query[valid_key], ['redpush_id']) # we don't want our internal id there
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
    