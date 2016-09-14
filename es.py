
import os
import re
import sys
import json
import click
import codecs
import requests

###
#
#	Global variables.
#
###

PATH_ES_CONFIG = 'es_config.json'
PATH_DATA_FOLDER = 'data/json_data_new/'

HOST_URL = 'http://localhost'
HOST_PORT = '9200'
BULK_INSERT_RATE = 1000
INDEX_NAME = 'lb'

#with open('../json_data_new/lb12079_5.json') as f:
#	d = json.loads(f.read())
#	print(json.dumps(d, indent=4, sort_keys=True))

###
#
#	CLI command functions.
#
###

@click.group(
	help='This is a command line interface for fetching and loading data from Litteraturbanken into an Elasticsearch instance.'
)
def cli():
	pass

@click.command(help='Check that the ES instance is up and running.')
def check_connection():
	
	# Make sure ES is up and running.
	try:
		response = es_get_query(HOST_URL + ':' + HOST_PORT, None)
		print('Elasticsearch is up and running!')
		print(json.dumps(response.json(), indent=4))
		print('\n')
	except requests.exceptions.RequestException as e:
		print(e)
		print('Failed to establish connection.\n')
		sys.exit(1)

@click.command(help='Create ES index.')
def create_index():

	# Get configuration.
	es_config = get_es_config()

	# Create new index
	es_post_query(
		HOST_URL + ':' + HOST_PORT + '/' + INDEX_NAME, 
		data=json.dumps({
			'settings': es_config['index_settings'],
			'mappings': {es_config['type_mappings']['name']: es_config['type_mappings']['mappings']}
		}), 
		credentials=(None, None)
	)

@click.command(help='Remove ES index and all its data entries.')
@click.option('--index', prompt='Index name', help='The index to be removed.')
def remove_index(index):
	
	# Get configuration.
	es_config = get_es_config()

	# Clear cache
	es_post_query(HOST_URL + ':' + HOST_PORT + '/' + index + "/_cache/clear", None)

	# Delete the index.
	es_delete_query(HOST_URL + ':' + HOST_PORT + '/' + index)


@click.command(help='Load data into ES.')
def load_data():

	# Get configuration.
	es_config = get_es_config()

	print('Inserting type: ' + es_config['type_mappings']['name'] + '\n')

	# Set hard limit
	hard_limit = float('inf') if es_config['type_mappings']['hard_limit'] == None else es_config['type_mappings']['hard_limit']

	counter = 0
	old_count = 0
	insert_str = ''
	for f in os.listdir(PATH_DATA_FOLDER):
		counter += 1

		# Prepare bulk to insert.
		data_file = codecs.open(PATH_DATA_FOLDER + '/' + f, 'r', 'utf-8-sig')
		json_obj = json.loads(remove_comments(data_file.read()))

		insert_str += json.dumps({'index': {'_index': INDEX_NAME, '_type': es_config['type_mappings']['name']}}) + '\n'
		insert_str += json.dumps(json_obj) + '\n'

		# Insert bulk
		if (counter % BULK_INSERT_RATE) == 0:
			print('Inserting entries: ' + str(old_count) + '-' + str(counter))

			try:
				es_post_query(HOST_URL + ':' + HOST_PORT + '/_bulk', insert_str)
			except requests.exceptions.RequestException as e:
				print(e)
				print('Post query failed.\n')
				sys.exit(1)

			old_count = counter + 1
			insert_str = ''

		# Check hard limit
		if counter >= hard_limit:
			break

	# Insert last bulk.
	if counter >= old_count:
		print('Inserting entries: ' + str(old_count) + '-' + str(counter))
		es_post_query(HOST_URL + ':' + HOST_PORT + '/_bulk', insert_str)
		print('\n')



###
#
#	ES communication functions.
#
###

def es_get_query(url, data=None, credentials=(None, None)):

	response = requests.get(url, data=data, auth=credentials)

	if response.status_code != 200:
		print('Reponse Code: ' + str(response.status_code))
		print('Response Info: ' + response.content.decode('utf8'))
		print('URL: ' + url)
		sys.exit(1)

	return response

def es_post_query(url, data=None, credentials=(None, None)):

	response = requests.post(url, data=data, auth=credentials)

	if response.status_code != 200:
		print('Reponse Code: ' + str(response.status_code))
		print('Response Info: ' + response.content.decode('utf8'))
		print('URL: ' + url)
		sys.exit(1)
	else:
		print('Post query successfully completed!\n')

def es_delete_query(url, credentials=(None, None)):

	response = requests.delete(url, auth=credentials)

	if response.status_code != 200:
		print('Reponse Code: ' + str(response.status_code))
		print('Response Info: ' + response.content.decode('utf8'))
		print('URL: ' + url)
		sys.exit(1)
	else:
		print('Delete query successfully completed!\n')



###
#
#	Help functions.
#
###

def get_es_config():

	with open(PATH_ES_CONFIG) as f:
		es_config = json.loads(f.read())

	return es_config

def remove_comments(string):

	return re.sub(re.compile("/\*.*?\*/", re.DOTALL ), '', string)

###
#
#	Main.
#
###

if __name__ == '__main__':

	cli.add_command(check_connection)
	cli.add_command(create_index)
	cli.add_command(remove_index)
	cli.add_command(load_data)

	print('\n')

	cli()