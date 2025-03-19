from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="face_detection_attendance",
    version="1.0.0",
    author="Parul University",
    author_email="youremail@example.com",
    description="A facial recognition-based attendance system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/Face_Detection_Attendance_System",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "attend=src.cli.main:main",
            "attend-train=src.cli.train:main",
            "attend-take=src.cli.take_attendance:main",
            "attend-view=src.cli.view_attendance:main",
        ],
    },
) 