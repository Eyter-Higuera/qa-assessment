@ignore
Feature: Reusable setup - provision a disposable Book Store account and authenticate

  # Called with `call read('classpath:bookstore/common/create-user.feature')`.
  # Returns { userName, password, userId, token, authHeader } to the caller.
  #
  # Every scenario gets its own throw-away account: the Book Store user namespace is
  # global and shared, so any fixed username would eventually collide (406 / 1204).

  Background:
    * url baseUrl

  Scenario: create an account and obtain a bearer token
    * def userName = karate.get('userName', 'qa_' + java.util.UUID.randomUUID() + '')
    * def password = karate.get('password', defaultPassword)
    # UUIDs contain hyphens; keep the name short and safe for the API.
    * def userName = userName.replace('-', '').substring(0, 20)

    Given path 'Account', 'v1', 'User'
    And request { userName: '#(userName)', password: '#(password)' }
    When method post
    Then status 201
    And match response == { userID: '#uuid', username: '#(userName)', books: [] }
    * def userId = response.userID

    Given path 'Account', 'v1', 'GenerateToken'
    And request { userName: '#(userName)', password: '#(password)' }
    When method post
    Then status 200
    And match response.status == 'Success'
    And match response.result == 'User authorized successfully.'
    And match response.token == '#string'
    * def token = response.token
    * def authHeader = 'Bearer ' + token
