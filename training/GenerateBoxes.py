import cv2
import numpy as np
import csv
import glob
import os
import math
from collections import defaultdict
#Find csv
csvs=glob.glob("C:/Users/Ben/Dropbox/HummingbirdProject/Completed_Frames/**/*.csv",recursive=True)

def mult(p,x):
    return(int(p+(p*x)))

def check_bounds(img,axis,p):
    if p > img.shape[axis]:
        p=img.shape[axis]
    if p < 0:
        p=0
    return(p)

crop_counter=0
for f in csvs:
    
    #1. Read in frames.csv
    with open(f) as frames:
        frame_file=csv.reader(frames)
        #skip header
        next(frame_file,None)
        
        ##get the largest box for each image
        image_areas=defaultdict(list)
        
        
        for row in frame_file:
            #test for correct format            
            if isinstance(eval(row[2]),float):
                break
            bbox=eval(row[2])
            area=(bbox[0][1]-bbox[1][1])*(bbox[1][0]-bbox[0][0])
            image_areas[row[1]].append([frame_file.line_num,area])
        
        #get max 
        biggest=[]
        for key, value in image_areas.items():
            if len(value)==0:
                continue
            biggest.append(value[np.argmax([x[0] for x in value] )][0])        
            
        #just proccess those line numbers
        for row in frame_file:
            
            print(frame_file.line_num)
            
            if frame_file.line_num in biggest:
                #read in image
                fname=os.path.split(f)[0] + "/" +row[1]+".jpg"
                img=cv2.imread(fname)
                if img is None:
                    print(fname + " does not exist")
                    continue
                
                #for image get the largest box
                
                #get bounding coordinates
                bbox=eval(row[2])
                            
                #expand box by multiplier m, limit to image edge
                m=math.sqrt(2)
                
                #max height
                p1=mult(bbox[1][1],-m)
                p1=check_bounds(img, 0, p1)
                
                #min height
                p2=mult(bbox[0][1],m)            
                p2=check_bounds(img, 0, p2)            
    
                #min width
                p3=mult(bbox[0][0],-m)            
                p3=check_bounds(img, 1, p3)            
                
                #max width
                p4=mult(bbox[1][0],m)                        
                p4=check_bounds(img, 1, p4)            
            
                #create a mask, in case its bigger than image            
                current_image=img[p1:p2,p3:p4]
    
                #4. Resize Image
                resized_image = cv2.resize(current_image, (227, 227))             
                cv2.namedWindow("img")
                cv2.imshow("img", resized_image)
                k=cv2.waitKey(0)
                
                #Save image for scoring
                cv2.imwrite("G:/Crops/"+str(crop_counter) + ".jpg",resized_image) 
                crop_counter+=1