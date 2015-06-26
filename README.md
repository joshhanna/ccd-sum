# ccd-sum
ccd summarizer

# Usage
Eventually, this utility will make it's way to PyPI.  Now, however, you'll need to run it out of this repository.  To do so, first install lxml:

    easy_install lxml

Next, run the script from the top level of this repository like so:

    python ccdsum/sum.py 'data'  '/ClinicalDocument/recordTarget/patientRole/patient/administrativeGenderCode'
