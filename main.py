#!/usr/bin/env python

"""main.py - This file contains handlers that are called by taskqueue and/or
cronjobs."""
import logging

import webapp2
from google.appengine.api import mail, app_identity
from api import GuessANumberApi

from models import User, Game
#from google.appengine.ext import db
#import logging

class SendReminderEmail(webapp2.RequestHandler):
    def get(self):
        """Send a reminder email to each User with an email about games.
        Called every hour using a cron job"""
        app_id = app_identity.get_application_id()
        users = User.query(User.email != None)
        
        #logging.info('DEBUG DEBUG DEBUG')
        
        for user in users:
            games = Game.query(Game.user == user.key, Game.game_over == False, Game.cancel == False).fetch()
            if games:
                subject = 'This is a reminder'
                body = 'Hello {}, you still have {} incomplete Hangman games!'.format(user.name, len(games))
                mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                           user.email,
                           subject,
                           body)
        
        # Original Code
        # for game in games:
        #     logging.info(game)
        #     use = game.user.get()
        #     subject = 'This is a reminder!'
        #     body = 'Hello {}, you still have incomplete Hangman games!'.format(use.name)
        #     # This will send test emails, the arguments to send_mail are:
        #     # from, to, subject, body
        #     mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
        #                    use.email,
        #                    subject,
        #                    body)

        # for user in users:
        #     subject = 'This is a reminder!'
        #     body = 'Hello {}, try out Hangman!'.format(user.name)
        #     # This will send test emails, the arguments to send_mail are:
        #     # from, to, subject, body
        #     mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
        #                    user.email,
        #                    subject,
        #                    body)


class UpdateAverageMovesRemaining(webapp2.RequestHandler):
    def post(self):
        """Update game listing announcement in memcache."""
        GuessANumberApi._cache_average_attempts()
        self.response.set_status(204)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('/tasks/cache_average_attempts', UpdateAverageMovesRemaining),
], debug=True)
