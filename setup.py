from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="face_detection_attendance_system",
    version="1.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A facial recognition-based attendance management system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/face-detection-attendance-system",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Education",
        "Topic :: Office/Business",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "attendance=src.main:main",
            "attendance-train=src.cli.train:main",
            "attendance-take=src.cli.take_attendance:main",
            "attendance-view=src.cli.view_attendance:main",
        ],
    },
    keywords="face recognition, attendance, education, facial recognition, OpenCV",
) 