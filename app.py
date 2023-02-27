import os
import urllib.request

from flask import Flask, jsonify, request
from resume_shortlisting import main

app = Flask(__name__)


@app.route('/process-resumes', methods=['POST'])
def process_resumes_api():
    # Get the resumes from the request
    resumes = request.json['resumes']
    job_description = request.json['job_description']

    # Create a folder to store the resumes
    folder_name = 'resumes'
    os.makedirs(folder_name, exist_ok=True)

    # Download each resume and save it to the folder
    for i, resume in enumerate(resumes):
        if resume.startswith('http'):
            # If the resume is a URL, download the PDF version of it
            resume_filename = f'resume_{i}.pdf'
            resume_path = os.path.join(folder_name, resume_filename)
            urllib.request.urlretrieve(resume, resume_path)
        else:
            # If the resume is a file path, open it and save it to the folder
            with open(resume, 'rb') as f:
                resume_filename = f'resume_{i}{os.path.splitext(resume)[1]}'
                resume_path = os.path.join(folder_name, resume_filename)
                with open(resume_path, 'wb') as f2:
                    f2.write(f.read())

    # Process the resumes
    shortlisted_resumes = main(folder_name, job_description)

    # Return the shortlisted resumes
    return jsonify({'shortlisted_resumes': shortlisted_resumes})


if __name__ == '__main__':
    app.run(debug=True)
