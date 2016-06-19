Feature: User is registered/logged in upon connection
  Background: context setup
    Given client is instantiated

  @real_server
  Scenario: Register new user
    Given "username" and "password"
    When user connects
    And sends login data
    Then connection is successful
    And new user is created

  @real_server
  Scenario: Login with existing user
    Given "username" and "password"
    When user connects
    And sends login data
    And disconnects
    When user connects
    And sends login data
    Then connection is successful
    And user is logged in

  @real_server
  Scenario: Login with bad password
    Given "username" and "password"
    When user connects
    And sends login data
    And disconnects
    When user connects
    And sends bad login data
    Then login is denied
