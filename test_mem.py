import tracemalloc
tracemalloc.start()
import onnxruntime
import numpy
from PIL import Image
import aiogram
import requests
import wikipediaapi
current, peak = tracemalloc.get_traced_memory()
print(f"Peak memory: {peak / 10**6} MB")
