@ignore
Feature: Reusable teardown - remove a disposable Book Store account

  # Called with the { userId, token } returned by create-user.feature.
  # Teardown is deliberately tolerant: a leftover account is a cleanup problem,
  # not a product defect, and must not turn a green run red.

  Background:
    * url baseUrl

  Scenario: delete the account
    Given path 'Account', 'v1', 'User', userId
    And header Authorization = 'Bearer ' + token
    When method delete
    Then match [200, 204, 401] contains responseStatus
