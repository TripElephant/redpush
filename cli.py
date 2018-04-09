"""
    Tool to manage the queries, graphs and dashboardas in a redash server from yaml definitions.
    Treating all of them as code, so you can version control them as you should :-)
"""
import click
import requests
from ruamel import yaml
import redash
import difflib
import sys
from ruamel.yaml.compat import StringIO
from operator import itemgetter

def save_yaml(queries, filename):
    """
        Save the queries into yaml
    """
    stream = open(filename, 'w')
    yaml.scalarstring.walk_tree(queries)
    yaml.dump(queries, stream,Dumper=yaml.RoundTripDumper) 

def read_yaml(filename):
        """
            Load the queries from a yaml file
        """
        file = open(filename, 'r')
        contents = yaml.load(file, yaml.RoundTripLoader)
        return contents

def sort_queries(queries):
    """
        Sort the list of queries so we can compare them easily afterwards
    """
    # First short queries per id
    queries = sorted(queries, key=itemgetter('redpush_id'))
    # then each query, sort the properties alphabetically 
    sorted_keys = [] 
    for item in queries:
        my_sorted_dict = {}   
        for k in sorted(item):
            my_sorted_dict[k] = item[k]
        sorted_keys.append(my_sorted_dict)
    return sorted_keys

@click.group()
def cli():
    pass

@cli.command()
@click.option('--redash-url')
@click.option('--api-key', help="API Key")
@click.option('-o', '--out-file', help="File to store the queries", type=str)
@click.option('-v','--visualizations', is_flag=True, help='Get the visualizations also')
def dump(redash_url, api_key, out_file, visualizations):
    if out_file is None:
        click.echo('No out file provided')
        return
    server = redash.Redash(redash_url, api_key)
    queries = server.Get_Queries()

    if visualizations:
        queries = server.Get_Full_Queries(queries)
        
    save_yaml(queries, out_file)

@cli.command()
@click.option('--redash-url')
@click.option('--api-key', help="API Key")
@click.option('-i', '--in-file', help="File to read the queries from", type=str)
def push(redash_url, api_key, in_file):
    
    if in_file is None:
        click.echo('No file provided')
        return
    server = redash.Redash(redash_url, api_key)
    old_queries = server.Get_Queries()
    old_queries = server.Get_Full_Queries(old_queries)

    new = read_yaml(in_file)
    server.Put_Queries(old_queries, new)

@cli.command()
@click.option('--redash-url')
@click.option('--api-key', help="API Key")
@click.option('-i', '--in-file', help="File to read the queries from", type=str)
def diff(redash_url, api_key, in_file):
    
    if in_file is None:
        click.echo('No file provided')
        return
    server = redash.Redash(redash_url, api_key)
    old_queries = server.Get_Queries()
    old_queries = server.Get_Full_Queries(old_queries)
    old_sorted_queries = sort_queries(old_queries)

    old_stream = StringIO()
    yaml.scalarstring.walk_tree(old_sorted_queries)
    yaml.dump(old_sorted_queries, old_stream,Dumper=yaml.RoundTripDumper) 

    new_queries = read_yaml(in_file)
    new_sorted_queries = sort_queries(new_queries)

    new_stream = StringIO()
    yaml.scalarstring.walk_tree(new_sorted_queries)
    yaml.dump(new_sorted_queries, new_stream,Dumper=yaml.RoundTripDumper) 

    # diff = difflib.ndiff(old_stream.getvalue().strip().splitlines(),new_stream.getvalue().strip().splitlines())
    diff = difflib.HtmlDiff().make_file(old_stream.getvalue().strip().splitlines(),new_stream.getvalue().strip().splitlines(), "test.html")
    sys.stdout.writelines(diff)


@cli.command()
@click.option('--redash-url')
@click.option('--api-key', help="API Key")
@click.option('-o', '--out-file', help="File to store the queries", type=str)
def dashboards(redash_url, api_key, out_file):
    if out_file is None:
        click.echo('No out file provided')
        return
    server = redash.Redash(redash_url, api_key)
    dashboardas = server.Get_Dashboards()

    save_yaml(dashboardas, out_file)


if __name__ == '__main__':
    cli()
