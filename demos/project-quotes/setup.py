from pathlib import Path

from setuptools import find_packages, setup

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent


readme = ""
with open(BASE_DIR / "README.md", "r") as readme_file:
    readme = readme_file.read()


requirements = []
with open(BASE_DIR / "requirements.txt", "r") as req_file:
    for item in req_file:
        requirements.append(item)


setup(
    name="dcx-project-quotes",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    license="MIT",
    description=(
        "Example Django project using django-comments-ink to only "
        "with backend capabilities (no use of the JavaScript code)."
    ),
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Daniela Rus Morales",
    author_email="danirus@eml.cc",
    maintainer="Daniela Rus Morales",
    maintainer_email="danirus@eml.cc",
    url="http://pypi.python.org/pypi/django-comments-ink",
    install_requires=requirements,
    scripts=["manage.py"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Framework :: Django",
        "Natural Language :: English",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary",
    ],
    zip_safe=True,
)
