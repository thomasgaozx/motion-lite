import json
import io
import numpy

def serialize(arr, date_str):
    """
    generates a json dump
    """
    memfile = io.BytesIO()
    numpy.save(memfile, arr)
    memfile.seek(0)
    return json.dumps([memfile.read().decode('latin-1'), date_str])

def deserialize(arr_json):
    """
    returns (numpy_arr, date_str)
    """
    decoded = json.loads(arr_json).encode('latin-1')
    memfile = io.BytesIO()
    memfile.write(decoded[0])
    memfile.seek(0)
    return (numpy.load(memfile), decoded[1])