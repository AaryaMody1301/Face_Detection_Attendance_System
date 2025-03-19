import sys
print("Python version:", sys.version)
print("Python path:", sys.path)

try:
    import cv2
    print("OpenCV version:", cv2.__version__)
    print("OpenCV path:", cv2.__file__)
except ImportError as e:
    print("Error importing cv2:", e)

try:
    from cv2 import face
    print("OpenCV face module found")
except ImportError as e:
    print("Error importing cv2.face:", e)
    try:
        import sklearn
        print("scikit-learn found, version:", sklearn.__version__)
    except ImportError as e:
        print("Error importing sklearn:", e) 