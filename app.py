from flask import Flask, render_template, request, redirect,send_from_directory, url_for
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

import os
import time
from array import array
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
load_dotenv()

subscription_key = os.getenv('subscription_key')
endpoint = os.getenv('endpoint')
computervision_client = ComputerVisionClient(endpoint,CognitiveServicesCredentials(subscription_key))

dirname = os.path.dirname(__file__)

def read_local(read):
    # Call API with image and raw response (allows you to get the operation location)
    read_response = computervision_client.read_in_stream(read, raw=True)
    # Get the operation location (URL with ID as last appendage)
    read_operation_location = read_response.headers["Operation-Location"]
    # Take the ID off and use to get results
    operation_id = read_operation_location.split("/")[-1]

    # Call the "GET" API and wait for the retrieval of the results
    while True:
        read_result = computervision_client.get_read_result(operation_id)
        if read_result.status.lower () not in ['notstarted', 'running']:
            break
        time.sleep(5)
    l=[]
    if read_result.status == OperationStatusCodes.succeeded:
        
        for text_result in read_result.analyze_result.read_results:
            for line in text_result.lines:
                l.append(line.text)
    result=(' '.join(l))
    return result
    
       
def extractTextFromImage(read_image_url):
	read_response  = computervision_client.read(read_image_url ,  raw=True)
	result = ''
	# Get the operation location (URL with an ID at the end) from the response
	read_operation_location = read_response.headers["Operation-Location"]
	# Grab the ID from the URL
	operation_id = read_operation_location.split("/")[-1]
	
	# Call the "GET" API and wait for it to retrieve the results 
	while True:
		read_result = computervision_client.get_read_result(operation_id)
		if read_result.status not in ['notStarted', 'running']:
			break
		time.sleep(1)

	# Add the detected text to result, line by line
	if read_result.status == OperationStatusCodes.succeeded:
		for text_result in read_result.analyze_result.read_results:
			for line in text_result.lines:
				result = result + " " + line.text
				
	return result

app = Flask(__name__)


UPLOAD_FOLDER = 'static/uploads/'
app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# routes
@app.route("/", methods=['GET', 'POST'])
def main():
    return render_template("index.html")

@app.route("/submit", methods = ['GET', 'POST'])
def get_output():
    if request.method == 'POST':
        image_url = request.form.get('image_url')
    result = extractTextFromImage(image_url)
    return render_template("index.html", prediction = result, img_path = image_url)

@app.route("/upload-image", methods = ['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        file = request.files['file']
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filepath=os.path.join(app.config['UPLOAD_FOLDER'],filename)
            read_image= open(filepath, "rb")
            result = read_local(read_image) 
    return render_template("index.html" ,filename=filename,prediction=result)
  
if __name__ == '__main__':
    app.run(debug=True)   

 