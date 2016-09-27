#Hangman Game

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
1.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
1.  (Optional) Generate your client library(ies) with the endpoints tool.
 Deploy your application.

## How to play:
1. Create a user by using the create_user endpoint. You must provide an email and user name.
2. Create a new game by using the new_game endpoint. You can specify the amount of attempts you want (or leave it blank for a default amount) but must specify the user_name. The final score you get at the end of your game is affected by the total number of attempts you select as is explained below in the scoring guidelines. 
3. You can make a move in your hangman game by using the make_move endpoint. You must provide the urlsafe_game_key and select a guess. The guess must be a single letter. If you guess correctly, the game will inform you that the letter was found in the word and will display the new word state with that letter filled in the correct places. If the letter was not found, the game will inform you that the letter was not found and will not change the word state but will decrease your attempts_remaining value by 1. You can continue to play until you either find all the letters or if attempts_remaining equals 0. 

## Scoring Guidelines:
The score equation is: (attempts_allowed-(attempts_allowed-attempts_remaining))/(attempts_allowed). The value is stored as a float. The idea behind this was to try and normalize games based on the amount of total attempts the player was allowed to make. This makes it so that a game with 5 total attempts where the player perfectly guessed the word with no mistakes and a game with 10 total attempts where the player also perfectly guessed the word are considered equal and will both provide a score boost of 1 point. 
 
 
##Game Description:
Hangman is a simple guessing game. Each game begins with a random 'target'
word, and a maximum number of 'attempts'. 'Guesses' are sent to the `make_move`
endpoint which will reply with either: 'Letter Found', 'Letter not found' and 
'you win', or 'game over' (if the maximum number of attempts is reached).
Many different Hangman games can be played by many different Users at any
given time. Each game can be retrieved or played by using the path parameter
`urlsafe_game_key`.

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.
 - words.txt: List of commonly used english words.

##Endpoints Included:
- **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will raise a ConflictException if a User with 
    that user_name already exists.
    
- **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name, min, max, attempts
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name provided must correspond to an
    existing user - will raise a NotFoundException if not. Also creates a 
    game_history object that keeps track of player guesses and the state of 
    the hangman word. The guess must be within the word and mutliple guess of 
    the same letter is allowed. Also adds a task to a task queue to update the 
    average moves remaining for active games.
     
- **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.
    
- **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, guess
    - Returns: GameForm with new game state.
    - Description: Accepts a 'guess' and returns the updated state of the game.
    If this causes a game to end, a corresponding Score entity will be created.
    Will also update the game_history for a valid move. 
    
- **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database (unordered).
    
- **get_user_scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms. 
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.

- **get_average_attempts**
    - Path: 'games/average_attempts'
    - Method: GET
    - Parameters: none
    - Returns: StringMessage. 
    - Description: Gets the cached average moves remaining.
    
 <!-- - **get_active_game_count**
    - Path: 'games/active'
    - Method: GET
    - Parameters: None
    - Returns: StringMessage
    - Description: Gets the average number of attempts remaining for all games
    from a previously cached memcache key. -->

- **get_user_games**
    - Path: scores/user/{user_name}
    - Method: GET
    - Parameters: username, email
    - Returns: GameForms
    - Description: Finds all the selected user's games and lists them.

- **cancel_game**
    - Path: game/{urlsafe_game_key}/cancel
    - Method: PUT
    - Parameters: urlsafe_game_key
    - Returns: GameForm
    - Description: Finds game based on its urlsafe_game_key and then sets it's
    cancel property to True. The game is still retrievable by the user but further
    moves will not be able to be made. This is irreversible.

- **get_high_scores**
    - Path: high_scores
    - Method: GET
    - Parameters: RankingForm
    - Returns: ScoreForms
    - Description: Returns all Scores ordered by score descending. If there are ties in score it will order the most recent player first.

- **get_user_rankings**
    - Path: get_user_rankings
    - Method: GET
    - Parameters: none
    - Returns: RankForms
    - Description: Returns Rank of all players ordered by total_score (sum of scores for all games played by that player) descending. 

- **get_game_history**
    - Path: {urlsafe_game_key}/history
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: Game_HistoryForm
    - Description: Returns the history of moves that the player made along with the word state at that time within game.




##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.

 - **Game_History**
    - Stores the guesses and corresponding word_states for each individual guess.
    
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.

 - **Score**
    - Stores username, date of score, whether the user won or lost, the number of guesses the user made, and the current score of the game.
    
 - **Rank**
    - Records the username, the total_score (sum of all individual game scores) and rank (ordered by highest total score.
    
##Forms Included:
 - **Game_HistoryForm**
    - Represents the state of the game during the various moves made. Displays the guesses made, the word's current state and the output is a easy to read string that displays the various guesses and game states. 

 - **GameForm**
    - Representation of a Game's state (urlsafe_key, attempts_remaining,
    game_over flag, message, user_name).

 - **GameForms**
    - Used to represent multiple GameForm forms.

 - **NewGameForm**
    - Used to create a new game (user_name, min, max, attempts)

 - **RankingForm**
    - Used to select the amount of high scores the user wants displayed.

 - **RankForm**
    - Represents various user's rank. It displays the user name, the total score of the user and the rank relative to other players. 

- **RankForms**
    - Used to represent multiple RankForm forms.

 - **MakeMoveForm**
    - Inbound make move form (guess).

 - **ScoreForm**
    - Representation of a completed game's Score (user_name, date, won flag,
    guesses).

 - **ScoreForms**
    - Multiple ScoreForm container.
    
 - **StringMessage**
    - General purpose String container.