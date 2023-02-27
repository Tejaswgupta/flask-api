# -*- coding: utf-8 -*-
"""resume_shortlisting.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1AziOi1nI96-6ZN2N83D0uCzKhnUUYaYZ
"""


import io
import json
import os
from io import StringIO

import nltk
import pandas as pd
import PyPDF2
import regex as re
import sklearn
import spacy
import textdistance as td
from docx import Document
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

nltk.download('stopwords')
nltk.download('popular')
nlp = spacy.load('en_core_web_sm')
# NLTK stop words
stop_words = set(stopwords.words("english"))
# WordNetLemmatizer and PorterStemmer objects
wnl = WordNetLemmatizer()
stemmer = PorterStemmer()


def get_pdf_text(pdf_file):
    """Function to extract text from a pdf file"""
    with open(pdf_file, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text()
        return text


def get_docx_text(docx_file):
    """Function to extract text from a docx file"""
    document = Document(docx_file)
    text = []
    for para in document.paragraphs:
        text.append(para.text)
    return '\n'.join(text)


def gather(directory):
    """Function to gather the contents of all PDF and docx files in a directory into a dataframe"""
    pdfs = []
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if filename.endswith(".pdf"):
            text = get_pdf_text(filepath)
        elif filename.endswith(".docx"):
            text = get_docx_text(filepath)
        pdfs.append({"file_name": filename, "text": text})
    return pd.DataFrame(pdfs)


def extract_links_emails_phone_numbers(text):
    # Use a regex pattern to extract URLs
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    urls = re.findall(url_pattern, text)

    # Use a regex pattern to extract emails
    email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+')
    emails = re.findall(email_pattern, text)

    # Use a regex pattern to extract phone numbers
    phone_pattern = re.compile(r'\d{3}-\d{3}-\d{4}')
    phone_numbers = re.findall(phone_pattern, text)

    return urls, emails, phone_numbers


def remove_links_emails_phone_numbers(text):
    # Extract URLs, emails, and phone numbers
    urls, emails, phone_numbers = extract_links_emails_phone_numbers(text)

    # Remove URLs, emails, and phone numbers from text
    for url in urls:
        text = text.replace(url, '')
    for email in emails:
        text = text.replace(email, '')
    for phone_number in phone_numbers:
        text = text.replace(phone_number, '')

    return text


def remove_special_characters(text):
    # Remove all special characters
    text = re.sub(r'[^\w\s]+', '', text)

    return text


def process_text(text):
    """Function to lemmatize, tokenize, remove stop words, stem, and reduce redundancy"""
    # Tokenize the text
    tokens = word_tokenize(text)

    # Remove stop words
    tokens = [token.lower()
              for token in tokens if token.lower() not in stop_words]

    # Lemmatize and stem the tokens
    lemmatized_tokens = [wnl.lemmatize(token) for token in tokens]
    stemmed_tokens = [stemmer.stem(token) for token in lemmatized_tokens]

    # Reduce redundancy by only keeping unique tokens
    processed_text = list(set(stemmed_tokens))

    return processed_text


def _get_target_words(text):
    """
    Takes in text and uses Spacy Tags on it, to extract the relevant Noun, Proper Noun words that contain words related to tech and JD. 

    """
    target = []
    # sent = " ".join(text)
    doc = nlp(text)
    for token in doc:
        if token.tag_ in ['NN', 'NNP']:
            target.append(token.text)
    return " ".join(target)


def clean(text):
    text = remove_links_emails_phone_numbers(text)
    text = remove_special_characters(text)
    text = _get_target_words(text)
    text = process_text(text)
    return text


def do_tfidf(token):
    tfidf = TfidfVectorizer()
    words = tfidf.fit_transform(token)
    sentence = " ".join(tfidf.get_feature_names_out())
    return sentence


def match(resume, job_des):
    j = td.jaccard.similarity(resume, job_des)
    s = td.sorensen_dice.similarity(resume, job_des)
    c = td.cosine.similarity(resume, job_des)
    o = td.overlap.normalized_similarity(resume, job_des)
    total = (j+s+c+o)/4
    # total = (s+o)/2
    return total*100


def calculate_scores(resumes, job_description):
    scores = []
    for x in range(resumes.shape[0]):
        score = match(
            resumes['tf_idf'][x], job_description)
        scores.append(score)
    return scores


def main(dir_location: str, job_description: str):
    # Call the gather_pdfs function and pass the directory path as an argument
    df = gather(dir_location)

    # Extract links, emails and phone numbers from resume before cleaning
    df['urls'] = df['text'].apply(
        lambda x: extract_links_emails_phone_numbers(x)[0])
    df['emails'] = df['text'].apply(
        lambda x: extract_links_emails_phone_numbers(x)[1])
    df['phone_numbers'] = df['text'].apply(
        lambda x: extract_links_emails_phone_numbers(x)[2])

    # data cleaning and tf_idf
    df['initial_text'] = df['text']

    df['text'] = df['text'].apply(lambda x: clean(x))
    df = df.drop(df[df['text'].apply(lambda x: len(x) == 0)].index)
    df = df.reset_index().drop('index', axis=1)

    df['tf_idf'] = df['text'].apply(lambda x: do_tfidf(x))

    # clean and tf_idf the job posting text
    reference = clean(job_description)
    reference = do_tfidf(reference)

    # find
    df['scores'] = calculate_scores(df, reference)
    df = df.sort_values(by='scores', ascending=False)
    df = df.reset_index().drop('index', axis=1)

    return df.head(5)['file_name']
    # return df.head(5)['file_name'].to_json(orient="records", lines=True)


if __name__ == "__main__":
    d = main('resumes', '''
    Who are we:

We're incubated at IIT Kanpur and working on state-of-the-art reinforcement learning based traffic management system. We are looking for reinforcement learning experts to join our team.


Responsibilities:

Build and iterate over RL models
Suggest improvements and fix bugs
Work in an agile environment.
Integrate models with hardware.


Qualifications

Experience with Machine learning libraries
Experience with Reinforcement Learning
Experience with Python
Experience with Tensorflow/ PyTorch

    ''')
    print(d)
