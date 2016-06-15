Feature: register new user

  Scenario: valid user
    Given username and password
      | username     | password     |
      | testusername | testpassword |
    When registering
    Then new user is created

  Scenario: existing user
    Given username and password of existing user
      | username | password |
      | testusername | testpassword |
    When registering
    Then new user is not created