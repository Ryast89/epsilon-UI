import os
from inspect import getsourcefile
from os.path import abspath
import json
#import boto3
from replit import db
#set active directory to file location
directory = abspath(getsourcefile(lambda: 0))
#check if system uses forward or backslashes for writing directories
if (directory.rfind("/") != -1):
  newDirectory = directory[:(directory.rfind("/") + 1)]
else:
  newDirectory = directory[:(directory.rfind("\\") + 1)]
os.chdir(newDirectory)


def initJsonData():
  f = open("db_init.json")
  data = json.load(f)
  f.close()
  for key in data:
    db[key] = data[key]
