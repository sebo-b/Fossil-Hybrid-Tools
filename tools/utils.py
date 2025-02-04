
import argparse
import json
import os
import re
from jsonschema import validate, ValidationError
from wapp_tools.appmeta_schema import appmeta_schema
from math import isqrt


class FileChecker:

    @staticmethod
    def detectImage(buffer,quick = True):

        class DetectedImage:
            possibleRLE = False
            possibleRAW = False
            def isImage(self):
                return self.possibleRLE or self.possibleRAW

        ret = DetectedImage()

        if len(buffer) > 0xFFFF:    #max file size
            return ret

        w = isqrt(len(buffer))
        ret.possibleRAW = (w*w == len(buffer))

        ret.possibleRLE = (len(buffer) % 2 == 0)
        if ret.possibleRLE:
            ret.possibleRLE = buffer[-2:] == b'\xff\xff'
        if ret.possibleRLE and not quick:
            numOfPixels = sum(buffer[2:-2:2])
            ret.possibleRLE = (buffer[0]*buffer[1] == numOfPixels)

        return ret

    @staticmethod
    def detectJerry(buffer):

        class DetectedJerry:
            def __init__(self,v):
                self.value = bool(v)
            def __bool__(self):
                return self.value
            def isJerry(self):
                return bool(self)

        return DetectedJerry(buffer[:4] == b'JRRY')


class ResizeType(object):

    def __call__(self,s):
        m = re.match('([0-9]+)?(?:x([0-9]+))?$',s)
        if m is None:
             raise argparse.ArgumentTypeError("invalid value")
        return m.groups()


class AppMetaType(object):

    def __init__(self):
        pass

    def __call__(self,s):

        appmeta = {}

        try:
            with open(s,"r") as meta_f:
                appmeta = json.load(meta_f)
        except json.JSONDecodeError:
            raise argparse.ArgumentTypeError("not a valid JSON file")

        try:
            validate(appmeta,appmeta_schema)
        except ValidationError as jsonerr:
            if len(jsonerr.relative_path) == 1 and jsonerr.relative_path[0] == "version":
                raise argparse.ArgumentTypeError(f"format of version must be x.y.z")
            raise argparse.ArgumentTypeError(f"invalid json format: {jsonerr.message}")

        if not isinstance(appmeta['type'],int):
            appmeta['type'] = {
                "face": 1,
                "watchface": 1,
                "app": 2,
                "application": 2,
                }[appmeta['type']]

        return appmeta

class DirOrFileType(object):

    def __call__(self,param):

        if isinstance(param,str):
            param = [param]

        files = []
        for p in param:
            if os.path.isdir(p):
                files.extend(de.path for de in os.scandir(p) if de.is_file() )
            else:
                files.append(p)


        return files

def _deepIter(values):
    if not (isinstance(values,list) or isinstance(values,tuple)):
        yield values
    else:
        for i in values:
            yield from _deepIter(i)


class FlatExtendAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest, None)
        if items is None:
            items = []
        items.extend(_deepIter(values))
        setattr(namespace, self.dest, items)
