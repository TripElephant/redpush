"""
    Tool to manage the queries, graphs and dashboardas in a redash server from yaml definitions.
    Treating all of them as code, so you can version control them as you should :-)
"""
import click
import requests
from ruamel import yaml
import redash


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

@click.command()
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

@click.command()
@click.option('--redash-url')
@click.option('--api-key', help="API Key")
@click.option('-i', '--in-file', help="File to read the queries from", type=str)
def load(redash_url, api_key, in_file, visualizations):
    
    if in_file is None:
        click.echo('No file provided')
        return
    server = redash.Redash(redash_url, api_key)
    old = server.Get_Queries()

    new = redpush.Read_file(in_file)
    redpush.Put_Queries(old, new)

@click.command()
@click.option('--redash-url')
@click.option('--api-key', help="API Key")
def diff(redash_url, api_key):
    click.echo("diff")

if __name__ == '__main__':
    dump()
