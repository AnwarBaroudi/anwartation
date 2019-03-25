#anwartation
import sys, termios, tty, os, time
import csv
import subprocess


#####################
# Utility FUNctions #
#####################

# reads in individual characters, or arrow keys (which are 3 chars apiece)
def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        if ch == '\x1b':
        	ch += sys.stdin.read(2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

# get terminal dimensions
def terminal_size():
    import fcntl, termios, struct
    th, tw, hp, wp = struct.unpack('HHHH',
        fcntl.ioctl(0, termios.TIOCGWINSZ,
        struct.pack('HHHH', 0, 0, 0, 0)))
    return tw, th

def get_sep(filename):
	sep = ''
	if filename[-4:] == '.csv':
		sep = ','
	elif filename[-4:] == '.tsv':
		sep = '\t'
	else:
		print('unsupported file type, I only support .tsv and .csv right now')
		return -1
	return sep


# returns a list of lists with the contents of the file
def load_and_read_file(filename):
	sep = get_sep(filename)
	if sep == -1:
		return -1
	f = open(filename,'r')
	c = csv.reader(f,delimiter=sep)
	lol_contents = [row for row in c]
	f.close()
	return lol_contents

def print_content_sample(lst_row,si=0,ei=-1,curr_i=-1):
	if ei == -1:
		ei = len(lst_row)
	max_len = max([len(s) for s in lst_row])
	line1 = '|'
	line2 = '|'
	line3 = ' '
	for i in range(si,ei):
		col_num_str = str(i)
		col_len = max(len(col_num_str),len(lst_row[i])) + 1
		line1 += ' ' + col_num_str + (' ' * (col_len - len(col_num_str))) + '|'
		line2 += ' ' + lst_row[i] + (' ' * (col_len - len(lst_row[i]))) + '|'
		if i == curr_i:
			line3 += ' ^' + (' ' * (col_len + 1))
		else:
			line3 += ' ' * (col_len + 2)
	print(line1)
	print(line2)
	if curr_i != -1:
		print(line3)


# return the ansi strings
def up(n):
	return u"\u001b[{}A".format(n)
def down(n):
	return u"\u001b[{}B".format(n)
def forward(n):
	return u"\u001b[{}C".format(n)
def back(n):
	return u"\u001b[{}D".format(n)
# 0 for deleting all after cursor 
# 1 for deleting all before cursor
# 2 for deleting all
def del_all(n):
	return u"\u001b[{}J".format(n)

#######
# OOP #
#######

class AnDoc:

	def __init__(self,filename,relevant_cols,annotation_col,mode):
		self.filename = filename
		self.lol_contents = load_and_read_file(filename)
		self.relevant_cols = relevant_cols
		self.annotation_col = annotation_col
		self.mode = mode
		self.num_rows = len(self.lol_contents)
		if self.annotation_col == len(self.lol_contents[0]):
			self.annotations = ['' for _ in range(self.num_rows)]
		else:
			self.annotations = [row[self.annotation_col] for row in self.lol_contents]
		self.current_index = 0
		self.search = ''
		self.num_annotated = len([x for x in self.annotations if x != ''])

	def print_curr_annotation(self):
		sys.stdout.write(up(len(self.relevant_cols) + 21))
		sys.stdout.write(del_all(0))
		sys.stdout.write(down(1))
		#write instructions
		print('controls:')
		print()
		print('Right Arrow Key: Next')
		print('Left Arrow Key: Previous')
		print('Up Arrow Key: Next unannotated/instance of search term')
		print('Down Arrow Key: Previous unannotated/instance of search term')
		print('Space: Delete annotation')
		print('Delete: Go to beginning (only tested on mac)')
		print('Return: Go to end (only tested on mac)')
		print('` (top left button on Mac): Set search term, to delete search term enter an empty string')
		print('=: enter custom note, for annotations longer than a character')
		print('Tab: Save and Exit')
		print()
		print('Current Search Term: ' + self.search)
		print('Annotation Progress: {}/{}'.format(self.num_annotated,self.num_rows))
		print()
		si = max(0,self.current_index-4)
		se = min(self.num_rows,self.current_index+4)
		if self.current_index < 4:
			se = min(self.num_rows,8)
		if self.num_rows - self.current_index < 4:
			si = max(0,self.num_rows - 8)

		print_content_sample(self.annotations,si,se,self.current_index)
		for i in self.relevant_cols:
			print(self.lol_contents[self.current_index][i])
		print()

	def annotate(self,annotation):
		old_val = self.annotations[self.current_index]
		self.annotations[self.current_index] = annotation
		if annotation == '' and old_val != '':
			self.num_annotated -= 1
		elif annotation != '' and old_val == '':
			self.num_annotated += 1

	def read_input(self):
		if self.mode == 'char':
			return self.read_char_input()
		# will add more as more modes are added

	def read_char_input(self):
		c = getch()
		# check for special cases
		if c == '\x1b[C':
			self.current_index = min(self.num_rows - 1, self.current_index + 1)
		elif c == '\x1b[D':
			self.current_index = max(0, self.current_index - 1)
		elif c == '\x1b[A':
			if self.current_index+1 == self.num_rows:
				return
			for i in range(self.current_index+1,self.num_rows):
				if self.annotations[i] == self.search or i == self.num_rows-1:
					self.current_index = i
					return
		elif c == '\x1b[B':
			if self.current_index == 0:
				return
			for i in range(self.current_index-1,-1,-1):
				if self.annotations[i] == self.search or i == 0:
					self.current_index = i
					return
		elif c == '\x7f':
			self.current_index = 0
		elif c == '\r':
			self.current_index = self.num_rows-1
		elif c == ' ':
			self.annotate('')
			self.current_index = min(self.num_rows - 1, self.current_index + 1)
			self.autosave()
		elif c == '`':
			sys.stdout.write('Enter a search term and press Return: ')
			self.search = input()
		elif c == '=':
			sys.stdout.write('Enter a note and press Return: ')
			note = input()
			self.annotate(note)
			self.current_index = min(self.num_rows - 1, self.current_index + 1)
			self.autosave()
		elif c == '\t':
			return -1
		else:
			self.annotate(c)
			self.current_index = min(self.num_rows - 1, self.current_index + 1)
			self.autosave()

	def make_lol_contents_with_annotations(self):
		self.lol_contents_with_annotations = [self.lol_contents[i][:self.annotation_col]
								 	 		  + [self.annotations[i]]
								 	 		  + self.lol_contents[i][self.annotation_col+1:]
								 	 		  for i in range(len(self.lol_contents))]

	def save_and_exit(self):
		sys.stdout.write(del_all(2))
		self.make_lol_contents_with_annotations()
		print('OK! here is the first row of your file again, with updated annotations:')
		print()
		print_content_sample(self.lol_contents_with_annotations[0])
		print()
		print('''
			  If you would like to leave your file formatted as is, 
			  just press Enter/Return.
			  If you would like to change the order of your rows, 
			  or exclude rows, type the column numbers, 
			  seperated by commas, in the order that you
			  wish them to show up in your new file, excluding any numbers
			  corresponding to columns you wish to exclude.
			  ''')
		str_new_order = input()
		if str_new_order != '':
			new_order = eval('[' + str_new_order + ']')
		else:
			new_order = []
		print()
		print('''
			  If you would like to overwrite your previous file, 
			  just press Enter/Return.
			  If you would like to write to a new file, simply type in 
			  the desired filename (the file does not have to exist yet). 
			  Make sure it ends in either .tsv or .csv
			  (more file types may be supported at a later date)
			  ''')
		new_filename = input()
		if new_filename == '':
			new_filename = self.filename
		self.write_to_new_file(new_filename,new_order)

	def write_to_new_file(self,filename,order):		
		sep = get_sep(filename)
		if sep == -1:
			filename = 'temp.tsv'
			sep = '\t'
		f = open(filename,'w')
		c = csv.writer(f,delimiter=sep)
		for row in self.lol_contents_with_annotations:
			if order:
				c.writerow([row[i] for i in order])
			else:
				c.writerow(row)
		f.close()
		print('file written to: ' + filename)

	def autosave(self):
		self.make_lol_contents_with_annotations()
		sep = '\t'
		f = open('autosave/autosave.tsv','w')
		c = csv.writer(f,delimiter=sep)
		for row in self.lol_contents_with_annotations:
			c.writerow(row)
		f.close()	




#####################
# Startup functions #
#####################


def collect_key_info():
	sys.stdout.write(del_all(2))
	print('hello!')
	print()
	print('please enter the filename which you would like to annotate, followed by the enter key')
	print()
	filename = input()
	lol_contents = load_and_read_file(filename)
	print()
	print('here is a sample row from this file:')
	print()
	print_content_sample(lol_contents[0])
	print()
	print('''
		  please list the column numbers you wish to see 
		  while you annotate seperated by commas,
		  i.e. type 0,2,3 and then press enter 
		  ''')
	print()
	str_relevant_cols = input()
	relevant_cols = eval('[' + str_relevant_cols + ']')
	print()
	print('great!')
	print()
	print('''
		  if this document is already partially annotated,
		  please type the column number where those annotations
		  go and then hit enter.
		  If it is not partially annotated, just hit enter and 
		  a new column will be made.
		  ''')	
	print()
	str_col_num = input()
	sys.stdout.write(del_all(2))
	if str_col_num == '':
		annotation_col = len(lol_contents[0])
	else:
		annotation_col = int(str_col_num)
	# add support for other nodes later
	mode = 'char'
	andoc = AnDoc(filename,relevant_cols,annotation_col,mode)
	return andoc

############################
# Run main annotation loop #
############################

def run_annotation_loop(andoc):
	while True:
		andoc.print_curr_annotation()
		ex = andoc.read_input()
		if ex == -1:
			break
	andoc.save_and_exit()
	print('yaay hope this worked well for you!')


def main():
	andoc = collect_key_info()
	subprocess.run(["mkdir", "autosave"])
	run_annotation_loop(andoc)
	subprocess.run(["rm","-r","autosave"])

if __name__ == '__main__':
	main()






