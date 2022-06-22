# django-comments-ink

django-comments-ink is a Django pluggable application that adds comments to your project. It extends the once official [Django Comments Framework](https://pypi.python.org/pypi/django-contrib-comments).

## Features

1. Comment can be nested.
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

It will install **Django**, **django-contrib-comments** and **django-rest-framework**.

## Quick start

To get started using django-comments-ink we will use the basic django blog example provided in the [tutorial.tar.gz](https://github.com/django-comments-ink/docs/assets/tutorial.tar.gz) tarball.

!!! note "Use your own Django project"

    If you have your own Django project ready then ignore the steps that refer to the tutorial bundle and the creation of the virtual environment. Just follow the relevant information that refers only to django-comments-ink.

### Start with the tutorial bundle

Create a virtual environment, install django-comments-ink, download the [tutorial.tar.gz](https://github.com/django-comments-ink/docs/assets/tutorial.tar.gz) bundle, extract the content, and set up the project:

    $ python3 -m venv venv
    $ source venv/bin/activate
    (venv)$ pip install django-comments-ink
    (venv)$ wget the-tutorial-link-from-above
    (venv)$ tar -xvzf tutorial.tar.gz
    (venv)$ cd tutorial
    (venv)$ python manage.py migrate
    (venv)$ python manage.py loaddata fixtures/*.json
    (venv)$ python manage.py runserver

The loaded fixtures contain a user `admin` with password `admin`, the default site, and some blog posts.

### Add required settings

Make the following changes to your `settings.py` module. Add the `SITE_ID` only if it is not defined yet:

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
    # Customize the maximum thread level for comments to 2:
    # Comment 1 (level 0)
    #  |-- Comment 1.1 (level 1)
    #       |-- Comment 1.1.1 (level 2)
    #
    COMMENTS_INK_MAX_THREAD_LEVEL = 2

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


Visit your Django project's [admin site](http://localhost:8000/admin/sites/site/) and be sure that the domain field of the `Site` instance points to the correct domain (`localhost:8000` when running the default development server), as it will be used to create comment verification URLs, follow-up cancellations, etc.

And then run the `manage.py migrate` command to create the tables.

### Include URLs

Add django-comments-ink URLs to the project's `urls.py` module. Edit the file `tutorial/urls.py` and be sure it contains the following code:

    urlpatterns = [
        ...
        path(r'comments/', include('django_comments_ink.urls')),
        ...
    ]

### Modify HTML templates

We will modify two templates:

1. The blog post **list** template, to display the count of comments a blog post has received.
1. The blog post **detail** template, to display the list of comments.


#### 1. The list template

Edit the `template/blog/post_list.html` file, and modify the code to load the **static** and **comments** modules:

    {% extends "base.html" %}

    {% load static %}
    {% load comments %}

Before the `content` block add the `extra_css` block (defined in `base.html`) so that we load the `comments.css` stylesheet:

    {% block extra_css %}
    <link
      rel="stylesheet" type="text/css"
      href="{% static 'django_comments_ink/css/comments.css' %}"
    ></link>
    {% endblock %}

Within the `content` block, modify the template to look like in the following snippet:

    {% for object in object_list %}
      {% get_comment_count for object as comment_count %}
      <h3><a href="{{ object.get_absolute_url }}">{{ object.title }}</a></h3>
      <p class="date">
        Published {{ object.publish }}
        {% if comment_count %}
          &nbsp;
          <span class="emoji">&#128172;</span>
          <span class="small">{{ comment_count }}</span>
          &nbsp;
        {% endif %}
      </p>
      {{ object.body|truncatewords:30|linebreaks }}
    {% endfor %}

Given that we have not posted any comment we should not see any change in the output yet.

#### 2. The detail template

Edit the `template/blog/post_detail.html` template, and modify the code to load the **comments** and **comments_ink** modules:

    {% extends "base.html" %}

    {% load i18n %}
    {% load static %}
    {% load comments %}
    {% load comments_ink %}

Before the `content` block add the `extra_css` block so that we load the `comments.css` stylesheet:

    {% block extra_css %}
    <link
      rel="stylesheet" type="text/css"
      href="{% static 'django_comments_ink/css/comments.css' %}"
    ></link>
    {% endblock %}

At the end of the `content` block, right before the `endblock` tag, add the following content:

    <div class="{% dci_custom_selector %}">
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
    <div class="{% dci_custom_selector %} pb32">
        {% render_inkcomment_list for object %}
    </div>
    {% endif %}

    <div class="{% dci_custom_selector %}" data-dci="comment-form">
    <section class="comment-form">
        <h5 class="text-center">{% translate "Post your comment" %}</h5>
        {% render_inkcomment_form for object %}
    </section>
    </div>

With those changes the Django project is ready to handle posting comments and listing them. It's the minimal installation. Try to send a comment and see the count in the list of posts. If you want to add reactions and add more dynamism, the minimal installation falls short.

Include the JavaScript plugin in your template to make posting comments more dynamic. Add the following block to the `template/blog/post_detail.html` to handle sending the comments via the JavaScript plugin:

    {% block extra_js %}
    <script src="{% static 'django_comments_ink/dist/dci-0.1.0.js' %}"></script>
    {% endblock %}
