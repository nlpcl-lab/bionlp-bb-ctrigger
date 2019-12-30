#Unsupervised inference of implicit biomedical events using context triggers

This repository contains source codes and datasets for the paper *Unsupervised inference of implicit biomedical events using context triggers* (a manuscript under review).


##Prerequisites

+ Python 2.7
+ NLTK (for the WordNet lemmatizer and the Porter stemmer)
  e.g.) pip install nltk
+ NLTK WordNet package
  e.g.) python -c "import nltk; nltk.download('wordnet')"


##How to use

1) Unzip the attached file "bionlp-bb-ctrigger-dist.zip" and go to the directory where the main script 'main.py' is located.
2) Execute 'main.py' using Python without any command argument, i.e., run "python main.py".
3) Then, the prediction output on the input (the test dataset) will be generated as a single zip archive ("prediction-test-{date}.zip") under the directory "data\predicted_output_in_official_format\". 

The zip archive file created by the script includes output files (\*.a2) for each input file (\*.a1) in official BB-event format and can thus be directly used as input to the official evaluation service available at http://2016.bionlp-st.org.


##Contact

Jin-Woo Chung (jinwoo.chung@kaist.ac.kr)

