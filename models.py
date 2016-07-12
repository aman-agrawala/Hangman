"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
import logging
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email =ndb.StringProperty()

class Game_History(ndb.Model):
    # user = ndb.KeyProperty(required=True, kind='User')
    guesses = ndb.StringProperty(repeated=True)
    word_states = ndb.StringProperty(repeated=True)
    # game = ndb.KeyProperty(required=True, kind = 'Game')
    # game_progress = ndb.StructuredProperty(Game, repeated=True)
    def to_form(self):
        form = Game_HistoryForm()
        form.guesses = self.guesses
        form.word_states = self.word_states
        moves = ""
        for i in range(len(self.guesses)):
            moves = moves + "Guess #" + str(i) + ": " + self.guesses[i]
            moves = moves + " | Word State:" + self.word_states[i]
            moves = moves + " , "
        form.output = moves
        return form

class Game_HistoryForm(messages.Message):
    guesses = messages.StringField(1, repeated=True)
    word_states = messages.StringField(2, repeated=True)
    output = messages.StringField(3)

class Game(ndb.Model):
    """Game object"""
    target = ndb.StringProperty(required=True)
    attempts_allowed = ndb.IntegerProperty(required=True)
    attempts_remaining = ndb.IntegerProperty(required=True, default=5)
    game_over = ndb.BooleanProperty(required=True, default=False)
    user = ndb.KeyProperty(required=True, kind='User')
    word_state = ndb.StringProperty(required=True)
    cancel = ndb.BooleanProperty(required=True)
    current_guess = ndb.StringProperty(required=True)

    @classmethod
    def new_game(cls, user, attempts):
        """Creates and returns a new game"""
        
        with open('words.txt', 'r') as f:
            words = f.read().splitlines()

        word = words[random.randint(1,len(words))]
        word.lower()

        blanks = "".join('_' for i in word)

        if attempts < 1:
            raise ValueError('Attempts must be greater than or equal to 1')
        game = Game(user=user,
                    target=word.lower(),
                    attempts_allowed=attempts,
                    attempts_remaining=attempts,
                    game_over=False,
                    word_state = blanks,
                    cancel = False,
                    current_guess='')
        game.put()

        # game_key = ndb.Key(Game,)
        game_history = Game_History(guesses = [''], word_states = [blanks], parent=game.key)
        game_history.put()
        # game_history.game = ndb.Key(Game,game)
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.attempts_remaining = self.attempts_remaining
        form.game_over = self.game_over
        form.message = message
        form.word_state = self.word_state
        form.cancel = self.cancel
        form.current_guess = self.current_guess
        return form

    def end_game(self, won=False):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.game_over = True
        self.put()
        # Add the game to the score 'board'
        value = (self.attempts_allowed-(self.attempts_allowed-self.attempts_remaining))/float(self.attempts_allowed)
        score = Score(user=self.user, date=date.today(), won=won,
                      guesses=self.attempts_allowed - self.attempts_remaining, score=value)
        score.put()

        game_score = value
        rank = Rank.query().filter(Rank.user == self.user).get()
        logging.info('DEBUG DEBUG DEBUG')
        logging.info(rank)
        if rank:
            rank.total_score=rank.total_score+game_score
            rank.put()
        else:
            rank = Rank(user = self.user, total_score=game_score)
            rank.put()


    def update_game_state(self, loc, guess):
        state = list(self.word_state)
        for l in loc:
            state[l] = guess
        self.word_state = "".join(state)
        self.current_guess=guess
        self.put()
        return self.word_state

    def convert_game_to_form(self):
        return GameForm(urlsafe_key=self.key.urlsafe(), 
                        attempts_remaining=self.attempts_remaining,
                        game_over=self.game_over,
                        message='A game',
                        user_name=self.user.get().name,
                        word_state=self.word_state,
                        cancel = self.cancel)

    def cancel_game(self):
        self.cancel=True
        self.put()



class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    guesses = ndb.IntegerProperty(required=True)
    score = ndb.FloatProperty(required=True)

    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, won=self.won,
                         date=str(self.date), guesses=self.guesses, score=self.score)

class Rank(ndb.Model):
    user = ndb.KeyProperty(required=True, kind='User')
    total_score = ndb.FloatProperty(required=True)
    rank = ndb.IntegerProperty(default = 0)

    @classmethod
    def make_rankings(cls):
        ranks = Rank.query().order(-Rank.total_score)
        val = 1
        for rank in ranks:
            rank.rank = val
            val = val + 1
            rank.put()

    def to_form(self):
        return RankForm(user_name=self.user.get().name, total_score=self.total_score,
                        rank = self.rank)



class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    attempts_remaining = messages.IntegerField(2, required=True)
    game_over = messages.BooleanField(3, required=True)
    message = messages.StringField(4, required=True)
    user_name = messages.StringField(5, required=True)
    word_state = messages.StringField(6, required=True)
    cancel = messages.BooleanField(7, required=True)
    current_guess = messages.StringField(8,required=True)

class GameForms(messages.Message):
    "Return multiple GameForms"
    items = messages.MessageField(GameForm,1,repeated=True)

class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    attempts = messages.IntegerField(4, default=5)

class RankingForm(messages.Message):
    number_of_results = messages.IntegerField(1, default=-1)

class RankForm(messages.Message):
    user_name = messages.StringField(1, required=True)
    total_score = messages.FloatField(2, required=True)
    rank = messages.IntegerField(3, required=True)

class RankForms(messages.Message):
    items = messages.MessageField(RankForm,1,repeated=True)

class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    guess = messages.StringField(1, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    guesses = messages.IntegerField(4, required=True)
    score = messages.FloatField(5, required=True)

class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
