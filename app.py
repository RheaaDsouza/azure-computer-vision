from copyreg import constructor
from flask import Flask, render_template, request, redirect,send_from_directory, url_for
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

from array import array
import requests, os, uuid, time, json
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
load_dotenv()

subscription_key = os.getenv('subscription_key')
endpoint = os.getenv('endpoint')
computervision_client = ComputerVisionClient(endpoint,CognitiveServicesCredentials(subscription_key))

# Load the values from .env
'''
t_key = os.getenv('t_key')
t_endpoint = os.getenv('t_endpoint')
location = os.getenv('LOCATION')
'''
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

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'pdf'])

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

@app.route("/translator", methods=['GET', 'POST'])
def index_post():
    # Add your subscription key and endpoint
    t_key = "c9c3392706d94f5784ff59b99781e1a5"
    t_endpoint = "https://api.cognitive.microsofttranslator.com"
    location = "eastus"
    '''t_key= os.getenv('t_key')
    t_endpoint=os.getenv('t_endpoint')
    location= os.getenv('location')'''
    # Read the values from the form
    original_text = request.form.get('ex_text')
    print(original_text)
    target_language = request.form.get('language')
    print(target_language)
    
    path='/translate'
    params = {
    'api-version': '3.0',
    'to': [target_language]
    }
    constructed_url = t_endpoint + path
    # Set up the header information, which includes our subscription key
    headers = {
        'Ocp-Apim-Subscription-Key': t_key,
        'Ocp-Apim-Subscription-Region': location,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }
    # Create the body of the request with the text to be translated
    body = [{ 'text': original_text }]
    translator_request = requests.post(constructed_url,params=params, headers=headers, json=body)
    translator_response = translator_request.json()
    print(json.dumps(translator_response, sort_keys=True, ensure_ascii=False, indent=4, separators=(',', ': ')))
    translated_text = translator_response[0]['translations'][0]['text']
    
    #Passing the translated text,original text, and target language to the template
    return render_template('translator.html', translated_text=translated_text)
  
if __name__ == '__main__':
    app.run(debug=True)   

 