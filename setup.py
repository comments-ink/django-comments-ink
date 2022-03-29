from pathlib import Path

from setuptools import setup, find_packages


BASE_DIR = Path(__file__).resolve().parent


readme = ""
with open(BASE_DIR / "README.md", "r") as readme_file:
    readme = readme_file.read()


requirements = []
with open(BASE_DIR / "requirements.txt", "r") as req_file:
    for item in req_file:
        requirements.append(item)


tests_requirements = requirements[:]
with open(BASE_DIR / "requirements-tests.txt", "r") as req_file:
    req_file.readline()  # Skip 1st line: '-r requirements.txt'.
    for item in req_file:
        tests_requirements.append(item)


dev_requirements = tests_requirements[:]
with open(BASE_DIR / "requirements-dev.txt", "r") as req_file:
    req_file.readline()  # Skip 1st line: '-r requirements-tests.txt'.
    for item in req_file:
        dev_requirements.append(item)


setup(
    name="django-comments-ink",
    version="1.0.0",
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
    url="http://pypi.python.org/pypi/django-comments-ink",
    install_requires=requirements,
    extras_requires={
        'tests': tests_requirements,
        'dev': dev_requirements,
    },
    setup_requires=['wheel'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Framework :: Django',
        'Natural Language :: English',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary',
    ],
    test_suite="dummy",
    zip_safe=True
)
