
import datetime
import json
import os
import re
import sys
import shutil

from bs4 import BeautifulSoup
from dateutil import parser

# Constants
FAKSIMIL_META_PATH = '../faksimil/'
FAKSIMIL_CONTENT_PATH = '../faksimil_v2/'
FAKSIMIL_META_EXT = '-faksimil-workdb'
FAKSIMIL_CONTENT_EXT = '-faksimil'
FAKSIMIL_OUTPUT_PATH = '../json_data_new/'

ETEXT_META_PATH = '../etext/'
ETEXT_CONTENT_PATH = '../etext/'
ETEXT_META_EXT = '-etext-workdb'
ETEXT_CONTENT_EXT = ''
ETEXT_OUTPUT_PATH = '../json_data_new/'

# Functions
def isMetaData(f, meta_ext):
	if meta_ext in f:
		return False
	return True


def saveToFile(file_name, page_idx, page_content, page_meta, output_path):

	json_dict = {
		'file_idx': file_name,
		'page_idx': page_idx,
		'page_content': page_content,
		'meta_info': page_meta
	}

	with open(output_path + file_name + '_' + page_idx + '.json', 'w', encoding='utf-8') as outfile:
		json.dump(json_dict, outfile, indent=4, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def parseFile(file_name, meta_path, content_path, meta_ext, content_ext, output_path):

	try:

		meta_soup = BeautifulSoup(open(meta_path + file_name + meta_ext + '.xml'), 'lxml-xml')
		meta_data = {}

		
		# Strings
		def parseString(key, fallback):
			try:
				meta_data[key] = meta_soup.find(key).string
			except:
				meta_data[key] = fallback

		parseString('lbworkid', None)
		parseString('mediatype', None)
		parseString('titleid', None)
		parseString('title', None)
		parseString('shorttitle', None)
		parseString('sortkey', None)
		parseString('texttype', None)
		parseString('keyword', None)
		parseString('show', None)
		parseString('edition', None)
		parseString('language', None)
		parseString('searchable', None)
		parseString('proofread', None)
		parseString('fraktur', None)
		parseString('printed', None)
		parseString('modernized', None)
		
		# Dates
		def parseDate(key, fallback):
			try:
				return str(parser.parse(meta_soup.find(key).string, default=datetime.date(1970, 1, 1)))
			except:
				try:
					return str(parser.parse(meta_soup.find(key).string[0:4], default=datetime.date(1970, 1, 1)))
				except:
					return fallback

		imported = parseDate('imported', None)
		work_updated = parseDate('work-updated', None)
		workdb_updated = parseDate('workdb-updated', None)
		imprintyear = parseDate('imprintyear', None)
		
		meta_data['imported'] = imported
		meta_data['work-updated'] = work_updated
		meta_data['workdb-updated'] = workdb_updated
		meta_data['imprintyear'] = imprintyear

		# Nested (authorids, provenance, publisher)
		meta_data['authorid'] = {}
		meta_data['authorid']['authors'] = []
		meta_data['authorid']['editors'] = []
		meta_data['authorid']['translators'] = []
		meta_data['authorid']['illustrators'] = []
		meta_data['authorid']['scholars'] = []
		for node in meta_soup.findAll('authorid'):
			if (node.parent.name.lower() == 'lbwork'):
				if node.get('type') == None:
					meta_data['authorid']['authors'].append(node.string)
				elif node.get('type') == 'editor':
					meta_data['authorid']['editors'].append(node.string)
				elif node.get('type') == 'translator':
					meta_data['authorid']['translators'].append(node.string)
				elif node.get('type') == 'illustrator':
					meta_data['authorid']['illustrators'].append(node.string)
				elif node.get('type') == 'scholar':
					meta_data['authorid']['scholars'].append(node.string)

		meta_data['provenance'] = []
		for outer_node in meta_soup.findAll('provenance'):
			for inner_node in outer_node:
				if inner_node.name != None:
					meta_data['provenance'].append({
						inner_node.name: inner_node.string
					})

		meta_data['publisher'] = {}
		meta_data['publisher']['name'] = meta_soup.select('publisher name')[0].string
		meta_data['publisher']['place'] = meta_soup.select('publisher place')[0].string
		meta_data['publisher']['country'] = meta_soup.select('publisher country')[0].string
		
		# Parts
		parts = []
		soup_parts = meta_soup.findAll('part')
		for p in soup_parts:
		
			nested_parts = p.findAll('part')

			if len(nested_parts) == 0:

				end_page = p.find('endpagename')
				if end_page == None:
					end_page = p.find('startpagename')

				parts.append({
					'titleid': p.find('titleid').string,
					'title': p.find('title').string,
					'navshow': p.find('navshow').string,
					'listshow': p.find('listshow').string,
					'texttype': p.find('texttype').string,
					'startpagename': p.find('startpagename').string,
					'endpagename': end_page.string
				})
		

		# Parse pages
		
		lines = [line.rstrip('\n').strip() for line in open(content_path + f + content_ext + '.xml')]
		page_content = ''
		last_page_idx = None
		part_inside = False
		part_current = None
		replace_strings = ['<lb/>', '&#x00AD;']

		for l in lines:

			page = {}

			if '<pb' in l:

				# Part
				if len(parts) > 0:

					if part_inside == False:
						meta_data['part_info'] = part_current

						for p in parts:
							if last_page_idx == p['startpagename']:
								part_current = p
								part_inside = True

					if part_inside == True:
						meta_data['part_info'] = part_current

						for p in parts:
							if last_page_idx == p['endpagename']:
								part_current = None
								part_inside = False
					
				# Pattern
				page_name_pattern = 'n="(.+?)"'
				page_boundary_patterns = [
					'<pb(.+?)/>',
					'<pb(.+?)></pb>'
				]

				name_match = re.search(page_name_pattern, l)
				boundary_match = re.search('|'.join(page_boundary_patterns), l)
				splitted_line = l.split(boundary_match.group())
				#print(l)

				if last_page_idx:
					saveToFile(file_name, last_page_idx, page_content + splitted_line[0], meta_data, output_path)

				last_page_idx = [g for g in name_match.groups() if g != None][0]
				page_content = splitted_line[1]

			elif l != '':
				for rs in replace_strings:
					l = l.replace(rs, '')
					
				page_content += l

		saveToFile(file_name, last_page_idx, page_content + splitted_line[0], meta_data, output_path)

	except:
		print('\n\nERROR!')
		print('File name: ' + file_name)
		print('\n')
		sys.exit(0)


if __name__ == '__main__':

	print('\nPARSING FILES...\n')

	print('Removing and creating outputs.')
	if FAKSIMIL_OUTPUT_PATH == ETEXT_OUTPUT_PATH:
		if os.path.isdir(FAKSIMIL_OUTPUT_PATH):
			shutil.rmtree(FAKSIMIL_OUTPUT_PATH)
			os.makedirs(FAKSIMIL_OUTPUT_PATH)
		else:
			os.makedirs(FAKSIMIL_OUTPUT_PATH)
	else:
		if os.path.isdir(FAKSIMIL_OUTPUT_PATH):
			shutil.rmtree(FAKSIMIL_OUTPUT_PATH)
			os.makedirs(FAKSIMIL_OUTPUT_PATH)
		else:
			os.makedirs(FAKSIMIL_OUTPUT_PATH)

		if os.path.isdir(ETEXT_OUTPUT_PATH):
			shutil.rmtree(ETEXT_OUTPUT_PATH)
			os.makedirs(ETEXT_OUTPUT_PATH)
		else:
			os.makedirs(ETEXT_OUTPUT_PATH)

	print('Listing files.')
	faksimil_files = [f[:-13] for f in os.listdir(FAKSIMIL_META_PATH) if isMetaData(f, FAKSIMIL_META_EXT)]
	etext_files = [f[:-4] for f in os.listdir(ETEXT_META_PATH) if isMetaData(f, ETEXT_META_EXT)]
	
	print('Parsing Etext\n')
	counter = 1
	for f in etext_files:
	#if True:
	#	f = 'lb8548815'
		
		parseFile(
			file_name=f,
			meta_path=ETEXT_META_PATH,
			content_path=ETEXT_CONTENT_PATH,
			meta_ext=ETEXT_META_EXT,
			content_ext=ETEXT_CONTENT_EXT,
			output_path=ETEXT_OUTPUT_PATH
		)
		
		print(str(counter) + '/' + str(len(etext_files)))
		counter += 1
	
	print('Parsing Faksimil\n')
	counter = 1
	for f in faksimil_files:
	#if True:
	#	f = 'lb2483009'
		
		parseFile(
			file_name=f,
			meta_path=FAKSIMIL_META_PATH,
			content_path=FAKSIMIL_CONTENT_PATH,
			meta_ext=FAKSIMIL_META_EXT,
			content_ext=FAKSIMIL_CONTENT_EXT,
			output_path=FAKSIMIL_OUTPUT_PATH
		)
		
		print(str(counter) + '/' + str(len(faksimil_files)))
		counter += 1

	print('\nPARSING FINISHED!\n')



