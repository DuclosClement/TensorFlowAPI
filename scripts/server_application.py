# -*- coding: utf-8 -*-
""" Flask webservice application accepting HTTP POST request with JSON data
corresponding to a list of MNIST image to be classified.
See https://github.com/JoelKronander/TensorFlask for a detailed specification of
the JSON data excepted for the request.

Example:
    The webservice can for example be deployed using gunicorn:
    $gunicorn server:app
"""
import json
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
from label_image import classify
from retrain import training

# création de l'objet logger qui va nous servir à écrire dans les logs
logger = logging.getLogger()
# on met le niveau du logger à DEBUG, comme ça il écrit tout
logger.setLevel(logging.DEBUG)

# création d'un formateur qui va ajouter le temps, le niveau
# de chaque message quand on écrira un message dans le log
formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
# création d'un handler qui va rediriger une écriture du log vers
# un fichier en mode 'append', avec 1 backup et une taille max de 1Mo
file_handler = RotatingFileHandler('activity.log', 'a', 1000000, 1)
# on lui met le niveau sur DEBUG, on lui dit qu'il doit utiliser le formateur
# créé précédement et on ajoute ce handler au logger
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# création d'un second handler qui va rediriger chaque écriture de log
# sur la console
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)

UPLOAD_FOLDER = "/data/storage/"
ALLOWED_EXTENSIONS = set(['jpg', 'gif', 'png' , 'bmp'])

#Create the Flask application handling HTTP requests
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




@app.route('/train', methods=['POST'])
def trainRoad():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            if not os.path.isdir("/Disk/Logos/"+request.form['categorie']):
                os.mkdir("/Disk/Logos/"+request.form['categorie'])
            file.save(os.path.join('/Disk/Logos/'+ request.form['categorie'], filename))
            listCategories = [x[0] for x in os.walk("/Disk/Logos")]
            listCategories.pop(0)
            nbFiles = []
            categorieNonRemplie = ''
            nbFichiersDansCategorieNonRemplie = 0
            nbFichiersSuffisants = True
            i = 0

            while i < len(listCategories) and nbFichiersSuffisants == True:
                nbFiles.append(len(os.listdir(listCategories[i])))
                if  nbFiles[i] < 20:
                    nbFichiersSuffisants = False
                    categorieNonRemplie = listCategories[i]
                    nbFichiersDansCategorieNonRemplie = nbFiles[i]
                i = i + 1

            if nbFichiersSuffisants == False:
                categorieNonRemplie = categorieNonRemplie.replace('/Disk/Logos/','')
                return('Pas eu besoin de train pas encore assez d\'images dans la catégorie '+str(categorieNonRemplie)+', il n\'y a que '+str(nbFichiersDansCategorieNonRemplie)+' éléments')
            else:
                training()
                return('Fin du  training !')

@app.route('/listeClasse', methods=['POST'])
def listeClasse():
    if request.method == 'POST':
        listCategorie = [x[0] for x in os.walk("/Disk/Logos")]
        listCategorie.pop(0)
        result = [s.replace('/Disk/Logos/','') for s in listCategorie]
        jsonreturn = json.dumps(result)
        return jsonreturn


@app.route('/recognize', methods=['POST'])
def classify_mnist_images():
    """Unpacks the JSON data passed with the POST request and forwards it to the
    MNISTClassifier for classification"""
    if request.method == 'POST':
	# check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            logger.info(UPLOAD_FOLDER+filename)
            resp = jsonify([])
            try:
                logger.info('Avant appel tensorflow')
                classifications = classify(UPLOAD_FOLDER+filename)
                logger.info('Apres appel tensorflow')
                data = {
                    'responses'  : classifications,
                }
                resp = jsonify(data)
                resp.status_code = 200
                os.remove(UPLOAD_FOLDER+filename)
                return resp

            #Handle Internal Server Errors
            except Exception as excep:
                resp = bad_input("Unexpected server API error: {}"
                                 .format(excep))
                return resp

def bad_input(message):
    """Returns a 404 status code JSON response with the provided message"""
    response = jsonify({'message': message})
    response.status_code = 404
    return response
