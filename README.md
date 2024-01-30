#  django-comments-ink &nbsp;&nbsp;&nbsp; [![example workflow](https://github.com/comments-ink/django-comments-ink/workflows/tests/badge.svg)](https://github.com/comments-ink/django-comments-ink/actions/workflows/ci-pipeline.yml) [![Code Coverage](https://github.com/comments-ink/django-comments-ink/raw/main/coverage.svg)]((https://github.com/comments-ink/django-comments-ink/actions/workflows/ci-pipeline.yml))


A Django pluggable application that adds comments to your project.

The current main branch is the result of the long lasting work-in-progress of the rel-3.0.0 branch of django-comments-xtd.

![screenshot](https://github.com/comments-ink/django-comments-ink/raw/main/cover.png)

It extends [django-contrib-comments](https://pypi.python.org/pypi/django-contrib-comments) with the following features:

1. Comments can be nested.
1. Customizable maximum thread level.
1. Optional notifications on follow-up comments via email.
1. Mute links to allow cancellation of follow-up notifications.
1. Comment confirmation via email when users are not authenticated.
1. Authenticated users can send reactions to comments and to other objects.
1. Comment reactions and object reactions are customizable.
1. Comment voting, to list comments sorted by votes.
1. Comments pagination.
1. JavaScript plugin.

Example sites and tests work under officially Django [supported versions](https://www.djangoproject.com/download/#supported-versions>):

* Django 5.0, 4.2, 4.1

Additional Dependencies:

* django-contrib-comments >=2.2,<2.3
* djangorestframework >=3.14,<3.15

Check the sample sites:

 * [dci-project-quotes](https://github.com/comments-ink/dci-project-quotes): A project driven totally by Django, no JavaScript (yes, such sites still exist).
 * [dci-project-stories](https://github.com/comments-ink/dci-project-stories): This one uses both Django and the JavaScript plugin, 100% frontend framework free.
