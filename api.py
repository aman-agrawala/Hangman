# -*- coding: utf-8 -*-`
"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""

import re
import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, Score, Rank, Game_History
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms, GameForms, RankingForm, RankForm, RankForms, Game_HistoryForm
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'

@endpoints.api(name='hangman', version='v1')
class GuessANumberApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        try:
            game = Game.new_game(user.key, request.attempts)
        except ValueError:
            raise endpoints.BadRequestException('Attempts must be greater that'
                                                'or equal to 1!')

        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form('Good luck playing Hangman!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game.game_over:
            return game.to_form('Game already over!')
        elif game.cancel:
            return game.to_form('Cannot make a move in a cancelled game!')

        # Begin the procedure for guess checking. First we see if the input is a letter.
        # Then we test if the user is guessing the entire word in one shot.
        # If they aren't, we only allow the user to guess a letter at a time.
        msg = ''
        if request.guess.isalpha():
            guess = request.guess.lower()
            if request.guess == game.target:
                word_state = game.complete_game_state(guess)
                msg = 'Word Guessed Correctly!'
                game_history = Game_History.query(ancestor = game.key).get()
                game_history.guesses.append(guess)
                game_history.word_states.append(game.target)
                game_history.put()
            else:
            #guess = request.guess.lower()

                occurs = []
                for m in re.finditer(guess,game.target):
                    occurs.append(m.start()) #locations where the letter is found in target
            
                if len(request.guess) > 1:
                    raise endpoints.BadRequestException('Please guess 1 letter at a time or guess the entire word!')
                elif occurs:
                    word_state = game.update_game_state(occurs, guess)
                    msg = 'Letter Found!'
                    game_history = Game_History.query(ancestor = game.key).get()
                    game_history.guesses.append(guess)
                    game_history.word_states.append(word_state)
                    game_history.put()
                else:
                    msg = 'Letter not found!'
                    game.attempts_remaining -= 1


                    game_history = Game_History.query(ancestor = game.key).get()
                    game_history.guesses.append(guess)
                    game_history.word_states.append(game.word_state)
                    game_history.put()

        else:
            raise endpoints.BadRequestException('Please enter letters only! No symbols or numbers')
        # game.attempts_remaining -= 1
        #guess = request.guess.lower()

        #occurs = []
        #for m in re.finditer(guess,game.target):
        #  occurs.append(m.start()) #locations where the letter is found in target

        # if occurs:
        #     word_state = game.update_game_state(occurs, guess)
        #     msg = 'Letter Found!'
        #     game_history = Game_History.query(ancestor = game.key).get()
        #     game_history.guesses.append(guess)
        #     game_history.word_states.append(word_state)
        #     game_history.put()
        # else:
        #   msg = 'Letter not found!'
        #   game.attempts_remaining -= 1


        # if request.guess < game.target:
        #     msg = 'Too low!'
        # else:
        #     msg = 'Too high!'

        if game.attempts_remaining < 1:
            game.end_game(False)
            return game.to_form(msg + ' Game over!')
        elif game.word_state == game.target:
            game.end_game(True)
            return game.to_form(msg + ' Game over!')
        else:
            game.put()
            return game.to_form(msg)

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(message=memcache.get(MEMCACHE_MOVES_REMAINING) or '')

    @staticmethod
    def _cache_average_attempts():
        """Populates memcache with the average moves remaining of Games"""
        games = Game.query(Game.game_over == False).fetch()
        if games:
            count = len(games)
            total_attempts_remaining = sum([game.attempts_remaining
                                        for game in games])
            average = float(total_attempts_remaining)/count
            memcache.set(MEMCACHE_MOVES_REMAINING,
                         'The average moves remaining is {:.2f}'.format(average))

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='user/{user_name}/games',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self,request):
      user = User.query(User.name == request.user_name).get()
      if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
      games = Game.query(Game.user == user.key, Game.cancel == False, Game.game_over == False)
      #games.filter('')
      return GameForms(items=[game.convert_game_to_form() for game in games])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}/cancel',
                      name='cancel_game',
                      http_method='PUT')
    def cancel_game(self,request):
      game = get_by_urlsafe(request.urlsafe_game_key, Game)
      if game and game.game_over != True:
        game.cancel_game()
        return game.to_form('Game Cancelled!')
      elif game.game_over == True:
        raise endpoints.BadRequestException('Cannot cancel a finished Game!')
      else:
        raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=RankingForm,
                      response_message=ScoreForms,
                      path='high_scores',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self,request):
      scores = Score.query().order(-Score.score)      
      if request.number_of_results == -1:
        return ScoreForms(items=[score.to_form() for score in scores])
      else:
        results = scores.fetch(limit=request.number_of_results)
        return ScoreForms(items=[score.to_form() for score in results])

    @endpoints.method(response_message=RankForms,
                      path='rankings',
                      name='get_user_rankings',
                      http_method="GET")
    def get_user_rankings(self,request):
      Rank.make_rankings()
      ranks = Rank.query().order(Rank.rank)
      return RankForms(items=[rank.to_form() for rank in ranks])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=Game_HistoryForm,
                      path='{urlsafe_game_key}/history',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
      game = get_by_urlsafe(request.urlsafe_game_key, Game)
      game_history = Game_History.query(ancestor = game.key).get()
      return game_history.to_form()


# @endpoints.api(name='hangman', version='v1')
# class hangman(GuessANumberApi, remote.Service):


api = endpoints.api_server([GuessANumberApi])
