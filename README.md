# redpush
Tool to manage queries a dashboards in Redash as source code.

You can define them in some _YAML_ files and use the tool to manage them using the Redash API.

# How it works

To get it working you obviously need a Redash server and user with write access. Then you can use the tool to manage them. There are a few commands:

### dump

It connects to the Redash server to dump the current queries and visuals there. It removes some of the fields that are not worth to be exported. (just pass the `-o` to pass the output file).

### push

This tool is to upload the queries, visuals, and dashboards to a server. `-i` for the source file.

There are a few tricks used by the tool to be able to manage those queries in Redash. If you start from a file generated from the `dump` command, you will need to add a few things:

- `redpush_id` Each query and visualization needs this, it is a unique id (uint) (not repeated in any query in a redash deployment) for redpush to be able to track the queries. The tool doesn't check if they are repeated or not, that is up to your tests or how you manage the _YAML_ file.

- `redpush_dashboards` List of the names of the dashboards a visualization should be added to. (Not mandatory if a visualization is not part of a dashboard). If the dashboard is not created it will be created. Also the `row`, `column` and `size` that should have that widget in the dashboard. Check the example code in the readme to see how it works

### Archive

Provided a list of queries, and the server, all the queries that are in the server than match at least one of the following conditions will be archived:

- Not having a `redpush_id`.
- Being in the server but not in the file.


### diff

This is used to show the diff from server to file. It is still a work in progress and the output is not yet fully completed.

### dashboard

This is to serialize the dashboards from a redash server to  _yaml_. More for debugging purposes than anything else, as those files cannot be used for anything in the tool.


## Example file

```yaml

- name: 'An example query'
  description:
  redpush_id: 1002  # some UNIQUE ID that will be used to track this query
  query: |-
    SELECT * FROM Purchases
  data_source_id: 1
  visualizations:
  - description: ''
    redpush_id: 2 # some UNIQUE ID (inside the query) that will be used to track this visualization
    redpush_dashboards:
      - name: my-business # the name of a dashboard were to add this visual
        row: 1   # in which row you want this graph
        col: 0   # in which column, can be [0,1,2]
        size: small  # size of the widget, a row fits: 3 small, 2 medium, 1 big
    type: CHART
    options:
      bottomMargin: 50
      error_y:
        visible: true
        type: data
      minColumns: 2
      series:
        stacking: stack
        percentValues: false
        error_y:
          visible: true
          type: data
      globalSeriesType: line
      yAxis:
      - type: linear
        title:
          text: Purchases
      - rangeMax: 1000
        type: linear
        rangeMin: 0
        opposite: true
        title:
          text: ''
      minRows: 5
      sortX: true
      defaultColumns: 3
      xAxis:
        labels:
          enabled: true
        type: datetime
        title:
          text: ''
      defaultRows: 8
      customCode: |-
        // Available variables are x, ys, element, and Plotly
        // Type console.log(x, ys); for more info about x and ys
        // To plot your graph call Plotly.plot(element, ...)
        // Plotly examples and docs: https://plot.ly/javascript/
      legend:
        enabled: false
    name: Chart
```

## Development

The easiest way to use this project is using docker and virtualenv.

You can easily run a redash server locally using docker:

1. `docker-compose up -d`
2. Wait until all services are running and then `docker exec -it redpush_server_1 ./manage.py database create_tables`
3. Go to `localhost:5000` and finish the setup of Redash (you need to add one data source)

If you want to to start over the server, you can:

1. `docker-compose kill`
2. `docker-compose rm -v` to remove the volumes
3. `rm -rf clickhouse-data/ postgres-data/` to remove the data of the dbs
4. Create everything again

## Tricks used

Redash API is created to be used from a web UI tool, not from a tool like this. Some hacks are created for it to work. That's the `redpush_id` that was mentioned before. Those are also stored inside the redash server, but as the server doesn't allow to add new fields to the objects (rightfully so) we found that the `options` property it is a key/value anything goes. So we abuse it to store there the internal IDs that redpush uses to match the objects. The tool also when exporting/importing takes care of adding/removing it from the `options` and putting it as a property of the object.


## TODOs

- Error handling. Currently it doesn't handle the errors and expects everything to go smooth. _Wishful thinking_
- Creating new widgets doesn't mean that they will work, they need to be executed at least once. So far it needs to be done in the UI
- More documentation and examples
- Layouting tool isn't very flexible, and has some bugs
