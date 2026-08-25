@account @contract
Feature: Account API - registration, authentication and authorisation contracts

  Background:
    * url baseUrl
    * def uniqueName = function(){ return 'qa_' + java.util.UUID.randomUUID().toString().replace('-','').substring(0,16) }

  @smoke
  Scenario: registering a new user returns 201 and an empty collection
    * def name = uniqueName()
    Given path 'Account', 'v1', 'User'
    And request { userName: '#(name)', password: '#(defaultPassword)' }
    When method post
    Then status 201
    And match response == { userID: '#uuid', username: '#(name)', books: [] }
    * def userId = response.userID

    # Clean up immediately - this scenario owns nothing beyond registration.
    Given path 'Account', 'v1', 'GenerateToken'
    And request { userName: '#(name)', password: '#(defaultPassword)' }
    When method post
    Then status 200
    * call read('classpath:bookstore/common/delete-user.feature') { userId: '#(userId)', token: '#(response.token)' }

  Scenario: a password sitting exactly on the 8-character boundary is accepted
    # Boundary analysis on the documented rule "eight characters or longer":
    # 'Pas0rd!1' is the shortest string that satisfies every character class.
    * def name = uniqueName()
    Given path 'Account', 'v1', 'User'
    And request { userName: '#(name)', password: 'Pas0rd!1' }
    When method post
    Then status 201
    * def userId = response.userID
    Given path 'Account', 'v1', 'GenerateToken'
    And request { userName: '#(name)', password: 'Pas0rd!1' }
    When method post
    Then status 200
    And match response.status == 'Success'
    * call read('classpath:bookstore/common/delete-user.feature') { userId: '#(userId)', token: '#(response.token)' }

  Scenario Outline: registration rejects passwords that violate the documented policy - <label>
    Given path 'Account', 'v1', 'User'
    And request { userName: '#(uniqueName())', password: '<password>' }
    When method post
    Then status 400
    And match response.code == '1300'
    And match response.message contains 'Password'

    Examples:
      | password    | label                    |
      | abc         | below minimum length     |
      | Pas0rd!     | 7 chars - one below min  |
      | password    | no digit, upper or symbol|
      | PASSWORD1!  | no lowercase             |
      | password1!  | no uppercase             |
      | Password123 | no special character     |
      | Password!!  | no digit                 |

  Scenario: registering an existing username is rejected with 406
    * def account = call read('classpath:bookstore/common/create-user.feature')
    Given path 'Account', 'v1', 'User'
    And request { userName: '#(account.userName)', password: '#(account.password)' }
    When method post
    Then status 406
    And match response == { code: '1204', message: 'User exists!' }
    * call read('classpath:bookstore/common/delete-user.feature') account

  Scenario: authentication with the wrong password does not issue a token
    * def account = call read('classpath:bookstore/common/create-user.feature')
    Given path 'Account', 'v1', 'GenerateToken'
    And request { userName: '#(account.userName)', password: 'Definitely!Wrong9' }
    When method post
    # NOTE: the API answers 200 with status "Failed" instead of 401.
    # The assertion documents the *current* contract; the expected one is BUG-006.
    Then status 200
    And match response == { token: '#null', expires: '#null', status: 'Failed', result: 'User authorization failed.' }

    # /Authorized answers 404 "User not found!" for an existing user with a bad
    # password - the wrong semantics for a credential failure (BUG-007).
    Given path 'Account', 'v1', 'Authorized'
    And request { userName: '#(account.userName)', password: 'Definitely!Wrong9' }
    When method post
    Then status 404
    And match response == { code: '1207', message: 'User not found!' }
    * call read('classpath:bookstore/common/delete-user.feature') account

  Scenario: a protected resource cannot be read without a token
    * def account = call read('classpath:bookstore/common/create-user.feature')
    Given path 'Account', 'v1', 'User', account.userId
    When method get
    Then status 401
    And match response == { code: '1200', message: 'User not authorized!' }
    * call read('classpath:bookstore/common/delete-user.feature') account

  @security
  Scenario: one user's token cannot read or modify another user's collection
    # Guards against the classic broken-object-level-authorisation flaw: the server
    # must bind the token to its owner and not trust the userId in the payload.
    * def alice = call read('classpath:bookstore/common/create-user.feature')
    * def bob = call read('classpath:bookstore/common/create-user.feature')

    Given path 'Account', 'v1', 'User', bob.userId
    And header Authorization = alice.authHeader
    When method get
    Then status 401
    And match response.code == '1200'

    Given path 'BookStore', 'v1', 'Books'
    And header Authorization = alice.authHeader
    And request { userId: '#(bob.userId)', collectionOfIsbns: [ { isbn: '#(seededIsbn)' } ] }
    When method post
    Then status 401

    * call read('classpath:bookstore/common/delete-user.feature') alice
    * call read('classpath:bookstore/common/delete-user.feature') bob
