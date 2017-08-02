#!/bin/bash 

#ssh if needed
gcloud compute ssh cloudml 

#Start docker instance
sudo docker run -it --privileged -- gcr.io/api-project-773889352370/cloudmlengine 

#Startup script
git clone https://github.com/bw4sz/DeepMeerkat.git
cd DeepMeerkat/training

#make sure all requirements are upgraded
pip install -r requirements.txt

declare -r PROJECT=$(gcloud config list project --format "value(core.project)")
declare -r BUCKET="gs://${PROJECT}-ml"
declare -r MODEL_NAME="DeepMeerkat"
declare -r JOB_ID="${MODEL_NAME}_$(date +%Y%m%d_%H%M%S)"
declare -r GCS_PATH="${BUCKET}/${MODEL_NAME}/${JOB_ID}"

################    
#Mount directory
################

#make empty directory for mount
mkdir /mnt/gcs-bucket

#give it permissions
chmod a+w /mnt/gcs-bucket

#GCSFUSE
gcsfuse --implicit-dirs api-project-773889352370-ml ~/mnt/gcs-bucket

##########################
#Evaluation data
##########################

#extract eval frames to predict
cat /mnt/gcs-bucket/Hummingbirds/testingdata.csv  | cut -f 1 -d "," > eval_files.txt
#fix local mount path
sed "s|gs://api-project-773889352370-ml/|/mnt/gcs-bucket/|g" eval_files.txt  > jpgs.txt

#Batch prediction
JOB_NAME="${MODEL_NAME}_$(date +%Y%m%d_%H%M%S)"
JSON_INSTANCES=Instances_$(date +%Y%m%d_%H%M%S).json

#Embed images as .json
python images_to_json.py -o $JSON_INSTANCES $(cat jpgs.txt)
gsutil cp $JSON_INSTANCES gs://api-project-773889352370-ml/Hummingbirds/Prediction/$JOB_NAME/

gcloud ml-engine jobs submit prediction $JOB_NAME \
    --model=$MODEL_NAME \
    --data-format=TEXT \
    --input-paths=gs://api-project-773889352370-ml/Hummingbirds/Prediction/$JOB_NAME/$JSON_INSTANCES \
    --output-path=gs://api-project-773889352370-ml/Hummingbirds/Prediction/$JOB_NAME/ \
    --region=us-central1

##########################
#Out of sample predictions
##########################

gsutil cp gs://api-project-773889352370-ml/Hummingbirds/holdoutdata.csv .
head trainingdata.csv | cut -d ',' -f1 > eval.csv

#extract eval frames to predict
cat /mnt/gcs-bucket/Hummingbirds/holdoutdata.csv  | cut -f 1 -d ","  > eval_files.txt

#fix local mount path
sed "s|gs://api-project-773889352370-ml/|/mnt/gcs-bucket/|g" eval_files.txt  > jpgs.txt

#Batch prediction
JOB_NAME_holdout="${MODEL_NAME}_$(date +%Y%m%d_%H%M%S)"
JSON_INSTANCES=Instances_$(date +%Y%m%d_%H%M%S).json

#Embed images as .json
python images_to_json.py -o $JSON_INSTANCES $(cat jpgs.txt)
gsutil cp $JSON_INSTANCES gs://api-project-773889352370-ml/Hummingbirds/Prediction/$JOB_NAME_holdout/

gcloud ml-engine jobs submit prediction $JOB_NAME_holdout \
    --model=$MODEL_NAME \
    --data-format=TEXT \
    --input-paths=gs://api-project-773889352370-ml/Hummingbirds/Prediction/$JOB_NAME_holdout/$JSON_INSTANCES \
    --output-path=gs://api-project-773889352370-ml/Hummingbirds/Prediction/$JOB_NAME_holdout \
    --region=us-central1

#Wait for prediction to finish
gcloud ml-engine jobs stream-logs $JOB_NAME_holdout

#holdout
#Parse predictions and enter information into database, key, prediction, run, date
python ParsePredictions.py -input /mnt/gcs-bucket/Hummingbirds/Prediction/$JOB_NAME/ -output $JOB_NAME

gsutil cp "$JOB_NAME"_eval.csv gs://api-project-773889352370-ml/Hummingbirds/Prediction/Summary/

#eva;
python ParsePredictions.py -input /mnt/gcs-bucket/Hummingbirds/Prediction/$JOB_NAME_holdout/ -output $JOB_NAME_holdout

gsutil cp "$JOB_NAME_holdout"_holdout.csv gs://api-project-773889352370-ml/Hummingbirds/Prediction/Summary