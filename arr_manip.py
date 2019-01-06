import json
import io
import numpy

def serialize(arr):
    memfile = io.BytesIO()
    numpy.save(memfile, arr)
    memfile.seek(0)
    return json.dumps(memfile.read().decode('latin-1'))

def deserialize(arr_json):
    memfile = io.BytesIO()
    memfile.write(json.loads(arr_json).encode('latin-1'))
    memfile.seek(0)
    return numpy.load(memfile)