"""
Signals relating to django-comments-ink.
"""
from django.dispatch import Signal

# Sent just after a comment has been verified.
confirmation_received = Signal()


# Sent just after a user has muted a comments thread.
comment_thread_muted = Signal()


# Sent before the data in the REST POST comment form is validated.
# A receiver returning True will suffice to automatically add valid values
# to the CommentSecurityForm fields 'timestamp' and 'security_hash'. The
# intention is to combine a receiver with a django-rest-framework
# authentication class, and return True when the request.auth is not None.
should_request_be_authorized = Signal()


# Sent after a comment got a reaction.
comment_got_a_reaction = Signal()

# Sent after a comment got a reaction.
object_got_a_reaction = Signal()
