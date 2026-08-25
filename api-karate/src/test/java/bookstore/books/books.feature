@books @contract
Feature: Book Store API - catalogue and collection contracts

  Background:
    * url baseUrl
    * def account = call read('classpath:bookstore/common/create-user.feature')
    * def auth = account.authHeader
    * def userId = account.userId
    * configure afterScenario = function(){ karate.call('classpath:bookstore/common/delete-user.feature', account) }

  @smoke
  Scenario: the catalogue is publicly readable and every entry is well formed
    Given path 'BookStore', 'v1', 'Books'
    When method get
    Then status 200
    And match response.books == '#[_ > 0]'
    And match each response.books ==
      """
      {
        isbn: '#regex ^[0-9]{13}$',
        title: '#string',
        subTitle: '#string',
        author: '#string',
        publish_date: '#string',
        publisher: '#string',
        pages: '#number? _ > 0',
        description: '#string',
        website: '#string'
      }
      """
    # ISBNs are the collection's primary key - duplicates would corrupt every
    # add/delete operation downstream.
    * def isbns = karate.map(response.books, function(b){ return b.isbn })
    * def unique = karate.distinct(isbns)
    * match unique == isbns

  Scenario: requesting an ISBN that is not in the catalogue is rejected
    Given path 'BookStore', 'v1', 'Book'
    And param ISBN = '0000000000000'
    When method get
    Then status 400
    And match response == { code: '1205', message: 'ISBN supplied is not available in Books Collection!' }

  Scenario: adding the same book twice is rejected and does not duplicate the collection
    Given path 'BookStore', 'v1', 'Books'
    And header Authorization = auth
    And request { userId: '#(userId)', collectionOfIsbns: [ { isbn: '#(seededIsbn)' } ] }
    When method post
    Then status 201

    Given path 'BookStore', 'v1', 'Books'
    And header Authorization = auth
    And request { userId: '#(userId)', collectionOfIsbns: [ { isbn: '#(seededIsbn)' } ] }
    When method post
    Then status 400
    And match response == { code: '1210', message: "ISBN already present in the User's Collection!" }

    # The failed retry must not have corrupted state.
    Given path 'Account', 'v1', 'User', userId
    And header Authorization = auth
    When method get
    Then status 200
    And match response.books == '#[1]'

  Scenario: several books can be added in one request
    Given path 'BookStore', 'v1', 'Books'
    And header Authorization = auth
    And request { userId: '#(userId)', collectionOfIsbns: [ { isbn: '#(seededIsbn)' }, { isbn: '#(secondIsbn)' } ] }
    When method post
    Then status 201

    Given path 'Account', 'v1', 'User', userId
    And header Authorization = auth
    When method get
    Then status 200
    And match response.books == '#[2]'
    And match response.books[*].isbn contains only [ '#(seededIsbn)', '#(secondIsbn)' ]

  Scenario: deleting a book the user does not own is rejected
    Given path 'BookStore', 'v1', 'Book'
    And header Authorization = auth
    And request { isbn: '#(seededIsbn)', userId: '#(userId)' }
    When method delete
    Then status 400
    And match response.code == '1206'

  Scenario: replacing a book in the collection swaps it for the new ISBN
    Given path 'BookStore', 'v1', 'Books'
    And header Authorization = auth
    And request { userId: '#(userId)', collectionOfIsbns: [ { isbn: '#(seededIsbn)' } ] }
    When method post
    Then status 201

    Given path 'BookStore', 'v1', 'Books', seededIsbn
    And header Authorization = auth
    And request { userId: '#(userId)', isbn: '#(secondIsbn)' }
    When method put
    Then status 200
    And match response.books[*].isbn contains [ '#(secondIsbn)' ]
    And match response.books[*].isbn !contains [ '#(seededIsbn)' ]

  Scenario: clearing the whole collection empties it
    Given path 'BookStore', 'v1', 'Books'
    And header Authorization = auth
    And request { userId: '#(userId)', collectionOfIsbns: [ { isbn: '#(seededIsbn)' }, { isbn: '#(secondIsbn)' } ] }
    When method post
    Then status 201

    Given path 'BookStore', 'v1', 'Books'
    And header Authorization = auth
    And param UserId = userId
    When method delete
    Then status 204

    Given path 'Account', 'v1', 'User', userId
    And header Authorization = auth
    When method get
    Then status 200
    And match response.books == []

  @security
  Scenario: the collection cannot be modified without a bearer token
    Given path 'BookStore', 'v1', 'Books'
    And request { userId: '#(userId)', collectionOfIsbns: [ { isbn: '#(seededIsbn)' } ] }
    When method post
    Then status 401
    And match response == { code: '1200', message: 'User not authorized!' }

  @security
  Scenario: a malformed bearer token is rejected
    Given path 'Account', 'v1', 'User', userId
    And header Authorization = 'Bearer not.a.real.token'
    When method get
    Then status 401
    And match response.code == '1200'
