import os
import re

FAKSIMIL_PATH = '../faksimil/'
FAKSIMIL_EXT = '-faksimil-workdb'
FAKSIMIL_OUTPUT = '../faksimil_v2/'

def isMetaData(f):
	if FAKSIMIL_EXT in f:
		return False
	else:
		return True

if __name__ == '__main__':

	faksimil_files = [f[:-4] for f in os.listdir(FAKSIMIL_PATH) if isMetaData(f)]
	counter = 1

	# Edit faksimil
	for f in faksimil_files:


		file_path = FAKSIMIL_PATH + f + '.xml'
		lines = [re.sub('<lb:word[^<]+>|<w[^<]+>|</lb:word>|</w>', '', line).rstrip('\n').strip() for line in open(file_path)]
		
		inside_p = False
		text = ''
		buffered_lines = ''
		
		for l in lines:
			if '<p>' in l:
				inside_p = True
				text += l + '\n'
			elif '</p>' in l:
				inside_p = False
				text += buffered_lines + '\n'
				text += l + '\n'
				buffered_lines = ''
			elif inside_p:
				buffered_lines += l + ' '
			else:
				text += l + '\n'
		
		with open(FAKSIMIL_OUTPUT + f + '.xml', "w") as f:
			f.write(text)

		print(str(counter) + '/' + str(len(faksimil_files)))
		counter += 1