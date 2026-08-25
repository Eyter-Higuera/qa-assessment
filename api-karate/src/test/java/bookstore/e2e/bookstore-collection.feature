@e2e
Feature: Book Store - end-to-end collection journey over the REST API

  # The full journey required by the assessment, expressed at the API layer:
  #   register -> login -> search & add a book -> list the collection -> delete -> log out
  #
  # Each scenario provisions and disposes of its own account, so the feature can run
  # in parallel with itself and leaves no residue in the shared demo environment.

  Background:
    * url baseUrl
    * def bookSchema =
      """
      {
        isbn: '#string',
        title: '#string',
        subTitle: '#string',
        author: '#string',
        publish_date: '#string',
        publisher: '#string',
        pages: '#number',
        description: '#string',
        website: '#string'
      }
      """

  Scenario: a user registers, collects a book, reviews and removes it, then ends the session

    # ---------- 1. Register ----------
    * def account = call read('classpath:bookstore/common/create-user.feature')
    * def userId = account.userId
    * def token = account.token
    * def auth = account.authHeader
    * print 'provisioned account:', account.userName, userId

    # ---------- 2. Log in (authenticate and confirm the session is live) ----------
    Given path 'Account', 'v1', 'Authorized'
    And request { userName: '#(account.userName)', password: '#(account.password)' }
    When method post
    Then status 200
    # The endpoint answers with a bare JSON primitive rather than an object, so the
    # assertion tolerates either a real boolean or its string form.
    And match response == '#? _ == true || _ == "true"'

    Given path 'Account', 'v1', 'User', userId
    And header Authorization = auth
    When method get
    Then status 200
    And match response.username == account.userName
    And match response.books == []

    # ---------- 3. Search the catalogue and add a book to the collection ----------
    Given path 'BookStore', 'v1', 'Books'
    When method get
    Then status 200
    And match response.books == '#[_ > 0]'
    And match each response.books == bookSchema
    # "Search" at the API layer is a client-side filter over the catalogue,
    # mirroring what the UI search box does.
    * def matches = karate.filter(response.books, function(b){ return b.title == seededTitle })
    * match matches == '#[1]'
    * def targetIsbn = matches[0].isbn
    * match targetIsbn == seededIsbn

    Given path 'BookStore', 'v1', 'Book'
    And param ISBN = targetIsbn
    When method get
    Then status 200
    And match response contains { isbn: '#(targetIsbn)', title: '#(seededTitle)' }
    And match response == bookSchema

    Given path 'BookStore', 'v1', 'Books'
    And header Authorization = auth
    And request { userId: '#(userId)', collectionOfIsbns: [ { isbn: '#(targetIsbn)' } ] }
    When method post
    Then status 201
    And match response.books == [ { isbn: '#(targetIsbn)' } ]

    # ---------- 4. See the list of my book collection ----------
    Given path 'Account', 'v1', 'User', userId
    And header Authorization = auth
    When method get
    Then status 200
    And match response.books == '#[1]'
    And match response.books[0] == bookSchema
    And match response.books[0] contains { isbn: '#(targetIsbn)', title: '#(seededTitle)', author: 'Richard E. Silverman' }

    # ---------- 5. Delete the book from my collection ----------
    Given path 'BookStore', 'v1', 'Book'
    And header Authorization = auth
    And request { isbn: '#(targetIsbn)', userId: '#(userId)' }
    When method delete
    Then status 204

    Given path 'Account', 'v1', 'User', userId
    And header Authorization = auth
    When method get
    Then status 200
    And match response.books == []

    # ---------- 6. Log out ----------
    # The API exposes no /logout: a session ends when the token stops being accepted.
    # Deleting the account is the observable end-of-session, and the assertion below
    # proves the token is genuinely dead rather than merely unused.
    * call read('classpath:bookstore/common/delete-user.feature') { userId: '#(userId)', token: '#(token)' }

    Given path 'Account', 'v1', 'User', userId
    And header Authorization = auth
    When method get
    # NOTE the mismatch: HTTP 401 carries error code 1207 ("User not found!"),
    # while /Account/v1/Authorized pairs that same code with HTTP 404. Asserted
    # as-is to lock the current behaviour; raised as BUG-008.
    Then status 401
    And match response == { code: '1207', message: 'User not found!' }
