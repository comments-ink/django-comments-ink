from pathlib import Path

from setuptools import find_packages, setup

BASE_DIR = Path(__file__).resolve().parent


readme = ""
with open(BASE_DIR / "README.md", "r") as readme_file:
    readme = readme_file.read()


requirements = []
with open(BASE_DIR / "requirements.in", "r") as req_file:
    for item in req_file:
        requirements.append(item)

setup(
    name="django-comments-ink",
    version="0.0.2",
    packages=find_packages(),
    include_package_data=True,
    license="MIT",
    description=(
        "Django pluggable commenting app with comment threads, follow-up "
        "notifications, mail confirmation, comment reactions and votes, and "
        "comment moderation. It supersedes django-comments-xtd."
    ),
    long_description=readme,
    long_description_content_type="text/x-rst",
    author="Daniela Rus Morales",
    author_email="danirus@eml.cc",
    maintainer="Daniela Rus Morales",
    maintainer_email="danirus@eml.cc",
    url="https://github.com/comments-ink/django-comments-ink",
    install_requires=requirements,
    setup_requires=["wheel"],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
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
    test_suite="dummy",
    zip_safe=True,
)
