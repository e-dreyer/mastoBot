from typing import Dict, Callable
import datetime
import json

def serialize_datetime(obj):
    """
    JSON serializer to help serialize dictionaries containing date_time objects
    """
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")

def toSerializableDict(data: Dict, serializer: Callable = serialize_datetime) -> Dict:
    """
    Takes a Python dictionary and serializes it to JSON and then converts it back to 
    a Python dictionary, using the default serializer or a custom one. This helps to serialize date_time
    objects
    
    Parameters
    ----------
    data: Dict
        The dictionary to convert to a serializable dictionary
    serializer: Callable
        The serializer to use, default = serialize_datetime
    """
    json_data = json.dumps(data, default=serializer)
    new_data = json.loads(json_data)
    return new_data
