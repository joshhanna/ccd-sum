import lxml
import os
import argparse
import re

from lxml import etree


class Summarizer:

	#Example:
	#{'/ClinicalDocument/templateId': 56, '/blah/blah': 45}
	CCD_count = {}
	#Example:
	#{'/ClinicalDocument/templateId': ['tag1', 'tag2'], '/blah/blah': ['tag3', 'tag5']}
	other_paths = {}
	#Example:
	#{'/ClinicalDocument/templateId': {'average': 23.4, 'max': 55, 'min': 2, 'examples': ['example1': 1, 'example2': 34, 'example3': 56]}, '/blah/blah': {'average': 5.6, 'max': 6, 'min': 5, 'examples': ['example1': 4, 'example2': 45, 'example3': 3]}}
	element_desc = {}
	#Example:
	#{/ClinicalDocument/templateId': {'root': {'with: 34, 'without': 55, 'total': 89, 'examples': ['ex1', 'ex2']}}, '/blah/blah': {'yadda': {'with': 6, 'without': 5, 'total': 11, 'examples': ['ex1', 'ex2']}}}
	attrib_desc = {}

	ccds_processed = 0
	
	def run(self, directory, paths, max_examples=10):

		# using xslt to remove namespaces from the documents to simplify
		xslt='''<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
					<xsl:output method="xml" indent="no"/>	

					<xsl:template match="/|comment()|processing-instruction()">
    					<xsl:copy>
      						<xsl:apply-templates/>
    					</xsl:copy>
					</xsl:template>

					<xsl:template match="*">
    					<xsl:element name="{local-name()}">
      						<xsl:apply-templates select="@*|node()"/>
    					</xsl:element>
					</xsl:template>

					<xsl:template match="@*">
    					<xsl:attribute name="{local-name()}">
      						<xsl:value-of select="."/>
    					</xsl:attribute>
					</xsl:template>
				</xsl:stylesheet>'''

		xslt_doc=etree.fromstring(xslt)
		transform=etree.XSLT(xslt_doc)

		print("Loading CCDs in " + directory)
		files = self._get_files(directory)
		docs = []

		for f in files:
			docs.append(transform(etree.parse(f)))

		print('processing documents')
		for doc in docs:
			self.ccds_processed += 1
			for path in paths:
				elements = doc.xpath(path)
				self._count_ccds(path, elements)
				self._find_other_paths(path, elements, doc)
				self._describe_elements(path, elements)
				self._describe_attribs(path, elements)

		for path in self.CCD_count.keys():
			print('******************************************************')
			print('* Summary for element  \'' + path + '\'')
			print('******************************************************')
			
			print('\n####################################')
			print('# Number of CCDs for each path')
			print('####################################')
		
			print('Num CCDs: ' + str(self.CCD_count[path]))

			print('\n####################################')
			print('# Other places element can be found')
			print('####################################')
			print('Other places: ')

			others = list(self.other_paths[path])
			others.sort()

			for other in others:
				print('\t' + other)

			print('\n####################################')
			print('# Element description')
			print('####################################')
			print('Minimum number found in one CCD: ' + str(self.element_desc[path]['min']))
			print('Maximum number found in one CCD: ' + str(self.element_desc[path]['max']))
			print('Average number found in one CCD: ' + str(self.element_desc[path]['average']))
			print('Total number found accross all CCDs: ' + str(self.element_desc[path]['total']))
			print('Examples: ')
			i = 0
			for example in self.element_desc[path]['examples']:
				if(i < max_examples):
					i += 1
					print('\t' + example)

			print('\n####################################')
			print('# Element attributes')
			print('####################################')
			print('Attributes:')
			for attrib in self.attrib_desc[path]:
				print('\n\tName: ' + attrib)
				print('\tElements with attribute: ' + str(self.attrib_desc[path][attrib]['with']) + ' (' + str((self.attrib_desc[path][attrib]['with'] / self.element_desc[path]['total']) * 100) + '%)')
				print('\tElements without attribute: ' + str(self.element_desc[path]['total'] - self.attrib_desc[path][attrib]['with']) + ' (' + str(((self.element_desc[path]['total'] - self.attrib_desc[path][attrib]['with']) / self.element_desc[path]['total']) * 100) + '%)')
				print('\tExamples: ')

				i = 0
				for example in self.attrib_desc[path][attrib]['examples']:
					if(i < max_examples):
						i += 1
						print('\t\t' + example)



	def _count_ccds(self, path, elements):
		if path not in self.CCD_count.keys():
			self.CCD_count[path] = 0
		
		if len(elements) > 0:
			self.CCD_count[path] += 1

	def _find_other_paths(self, path, elements, doc):
		if(not path in self.other_paths.keys()):
			self.other_paths[path] = set()

		if len(elements) > 0:
			tag_name = elements[0].tag
		else:
			return

		others = doc.xpath('//' + tag_name)
		for other in others:
			other_path = doc.getpath(other)
			other_path = re.sub(r'\[\d+?\]', '', other_path)
			if path != other_path:
				self.other_paths[path].add(other_path)

	def _describe_elements(self, path, elements):
		if(not path in self.element_desc.keys()):
			self.element_desc[path] = {}

		desc = self.element_desc[path]

		count = len(elements)

		if(not 'max' in desc.keys()):
			desc['max'] = count
		elif(desc['max'] < count):
			desc['max'] = count

		if 'total' not in desc.keys():
			desc['total'] = count
		else:
			desc['total'] += count 

		if(not 'min' in desc.keys()):
			desc['min'] = count
		elif(desc['min'] > count):
			desc['min'] = count

		if(not 'average' in desc.keys()):
			desc['average'] = count / self.ccds_processed
		else:
			desc['average'] = (((self.ccds_processed - 1) * desc['average']) + count) / (self.ccds_processed)

		if(not 'examples' in desc.keys()):
			desc['examples'] = set([el.text.strip() for el in elements if el.text and el.text.strip()])
		else:
			desc['examples'] |= set([el.text.strip() for el in elements if el.text and el.text.strip()])


	def _describe_attribs(self, path, elements):
		if(not path in self.attrib_desc.keys()):
			self.attrib_desc[path] = {}

		desc = self.attrib_desc[path]

		for el in elements:
			for attrib in el.keys():
				if attrib not in desc.keys():
					desc[attrib] = {'with': 1, 'examples': set([el.get(attrib) for el in [el] if el.get(attrib)])}
				else:
					desc[attrib]['with'] += 1
					desc[attrib]['examples'] |= set([el.get(attrib) for el in [el] if el.get(attrib)])
			


	def _get_files(self, directory):
		files = []
		for root, dirs, fs in os.walk(directory):
			for f in fs:
				if(f.endswith('.xml')):
					files.append(root + '/' + f)
		return files

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Summarize multiple CCD documents.')
	parser.add_argument('directory', metavar='dir', nargs=1, help='Top level directory of CCDs')
	parser.add_argument('path', metavar='path', nargs='+', help='Path of variable to summarize')

	args = parser.parse_args()

	summarizer = Summarizer();
	summarizer.run(args.directory[0], args.path)
		