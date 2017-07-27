import logging
import argparse
import json
import logging
import os
import csv
import apache_beam as beam
from DeepMeerkat import DeepMeerkat

class PredictDoFn(beam.DoFn):
  
  def process(self,element):
    MM=DeepMeerkat.DeepMeerkat()    
    MM.process_args() 
    
    #Assign input from DataFlow/manifest
    MM.input=element
    MM.run()

def run():
  parser = argparse.ArgumentParser(**kwargs)
  parser.add_argument('--input', dest='input', default="gs://api-project-773889352370-testing/DataFlow/manifest.csv",
                      help='Input file to process.')
  known_args, pipeline_args = parser.parse_known_args()
  
  p = beam.Pipeline(argv=pipeline_args)
  
  vids = (p|'Read input' >> beam.io.ReadFromText(known_args.input)
       | 'Parse input' >> beam.Map(lambda line: csv.reader([line]).next())
       | 'Run MotionMeerkat' >> beam.ParDo(PredictDoFn()))
  
  logging.getLogger().setLevel(logging.INFO)
  p.run()
  
if __name__ == '__main__':
  logging.getLogger().setLevel(logging.INFO)
  run()
