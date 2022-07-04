# django-comments-ink

django-comments-ink is a Django pluggable application that adds comments to your project. It extends the once official [Django Comments Framework](https://pypi.python.org/pypi/django-contrib-comments).

## Features

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

## Installation

    $ pip install django-comments-ink

It will install Django, django-contrib-comments and django-rest-framework.

## Quick start

To get started using django-comments-ink we will use the basic django blog example provided by the [dci-quick-start](https://github.com/comments-ink/dci-quick-start) project.

!!! note "Use your own Django project"

    If you have your own Django project ready then ignore the steps that refer to the tutorial bundle and the creation of the virtual environment. Just follow the relevant information that refers only to django-comments-ink.

### Setup quick-start project

Download the [quick-start project bundle](https://github.com/comments-ink/dci-quick-start/archive/refs/tags/v1.0.1.tar.gz), create a virtual environment, and set up the project:

``` bash title="Run in your terminal shell:"
git clone https://github.com/comments-ink/dci-quick-start
cd dci-quick-start
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd quick_start
python manage.py migrate
python manage.py loaddata fixtures/*.json
python manage.py runserver
```

The loaded fixtures contain the default site, users and some blog posts.

#### About the users

The project allows you to login using any of the users provided with the `users.json` fixture. There are 110 users. Here are the login email and password of the first 10. The rest follow the same pattern; the password is the left side of the email address:

 * `admin@example.com`, password `admin`
 * `fulanito@example.com`, password `fulanito`
 * `mengo@example.com`, password `mengo`
 * `daniela.rushmore@example.com`, password `daniela.rushmore`
 * `lena.rosenthal@example.com`, password `lena.rosenthal`
 * `amalia.ocean@example.com`, password `amalia.ocean`
 * `isabel.azul@example.com`, password `isabel.azul`
 * `joe.bloggs@example.com`, password `joe.bloggs`
 * `eva.rizzi@example.com`, password `eva.rizzi`
 * `david.fields@example.com`, password `david.fields`


### Add required settings

Make the following changes to your `quick_start/settings.py` file. Add the `SITE_ID` only if it is not defined yet:

``` py
SITE_ID = 1

INSTALLED_APPS = [
    ...
    'django.contrib.sites',
    ...
    'django_comments_ink',
    'django_comments',
    ...
]

COMMENTS_APP = 'django_comments_ink'

# --------------------------------------------------------------
# Customize the maximum thread level for comments to 1:
# Comment 1 (level 0)
#  |-- Comment 1.1 (level 1)
#
COMMENTS_INK_MAX_THREAD_LEVEL = 1

# --------------------------------------------------------------
# Set confirmation email to True to require comment confirmation
# by email for no logged-in users.
#
COMMENTS_INK_CONFIRM_EMAIL = True

# --------------------------------------------------------------
# Ignore this entry if you have already a working email backend.
# Otherwise use the console to output the outgoing email messages.
#
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Other email settings:
EMAIL_HOST = "smtp.mail.com"
EMAIL_PORT = "587"
EMAIL_HOST_USER = "alias@mail.com"
EMAIL_HOST_PASSWORD = "yourpassword"
DEFAULT_FROM_EMAIL = "Helpdesk <helpdesk@yourdomain>"
```

Visit your Django project's [admin site](http://localhost:8000/admin/sites/site/) and be sure that the domain field of the `Site` instance points to the correct domain (`localhost:8000` when running the default development server), as it will be used to create comment verification URLs, follow-up cancellations, etc. The admin user in the quick-start project is `admin@example.com`, password `admin`.

Having `django_comments_ink` and `django_comments` in your `INSTALLED_APPS` settings, run the `manage.py migrate` command to create the tables.

### Include URLs

Add the following changes to your `quick_start/urls.py` file:

``` py
urlpatterns = [
    ...
    path(r'comments/', include('django_comments_ink.urls')),
    ...
]
```

### Modify HTML templates

We will modify two templates:

1. The blog post **list** template, to display the count of comments a blog post has received.
1. The blog post **detail** template, to display the list of comments.


#### 1. The list template

Edit the `template/blog/post_list.html` file and modify the code to load the **static** and **comments** modules:

``` HTML
{% extends "base.html" %}

{% load i18n %}
{% load static %}
{% load comments_ink %}
```

Before the `content` block add the `extra_css` block (defined in `base.html`) so that we load the `comments.css` stylesheet:

``` HTML
{% block extra_css %}
<link
    rel="stylesheet" type="text/css"
    href="{% static 'django_comments_ink/css/comments.css' %}"
>
{% endblock %}
```

Within the `content` block, modify the template to look like in the following snippet:

``` HTML
{% for object in object_list %}
    {% get_inkcomment_count for object as comment_count %}
    <div>
    <h6 class="inline flex flex-align-center">
        <a href="{{ object.get_absolute_url }}">{{ object.title }}</a>
        - <span class="small">{{ object.publish|date:"d-F-Y" }}</span>
        {% if comment_count %}
        - <span class="emoji small">&#128172;</span>
        <span class="small">{{ comment_count }}</span>
        {% endif %}
    </h6>
    {{ object.body|truncatewords:30|linebreaks }}
    </div>
{% endfor %}
```

Given that we have not posted comments yet we should not see any change in the browser.

#### 2. The detail template

Edit the `template/blog/post_detail.html` template, and modify the code to load the **comments** and **comments_ink** modules:

``` HTML
{% extends "base.html" %}

{% load i18n %}
{% load static %}
{% load comments %}
{% load comments_ink %}
```

Before the `content` block add the `extra_css` block so that we load the `comments.css` stylesheet:

``` HTML
{% block extra_css %}
<link
    rel="stylesheet" type="text/css"
    href="{% static 'django_comments_ink/css/comments.css' %}"
>
{% endblock %}
```

At the end of the `content` block and before the closing tag of the `article` HTML element, add the following content:

``` HTML
    <div class="dci">
      {% get_inkcomment_count for object as comment_count %}
      {% if comment_count %}
      <h6 class="text-center">
        {% blocktrans count comment_count=comment_count %}
        There is {{ comment_count }} comment
        {% plural %}
        There are {{ comment_count }} comments
        {% endblocktrans %}
      </h6>
      {% endif %}
    </div>

    {% if comment_count %}
      <div class="dci pb32">
        {% render_inkcomment_list for object %}
      </div>
    {% endif %}

    <div class="dci" data-dci="comment-form">
      <section class="comment-form">
      <h5 class="text-center">{% translate "Post your comment" %}</h5>
      {% render_inkcomment_form for object %}
      </section>
    </div>
```

With those changes the Django project is ready to handle posting and listing comments. It's the minimal installation. Send a comment and see the count in the list of posts. Remember that emails are sent to the console.

Include the JavaScript plugin in your template to make posting comments more dynamic. The JavaScript plugin displays the comment reply form provided with the `comments/reply_template.html` file.

Add the following two blocks to the `template/blog/post_detail.html` to handle sending the comments via the JavaScript plugin:

``` HTML
{% block extra_html %}
{% render_comment_reply_template for object %}
{% endblock %}

{% block extra_js %}
<script src="{% static 'django_comments_ink/dist/dci-0.2.0.js' %}"></script>
{% endblock %}
```

Now sending comments and replies is enabled via the JavaScript plugin.
