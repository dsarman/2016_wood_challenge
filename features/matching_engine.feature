Feature: Each order is matched upon receipt

  @fake_server
  Scenario: Full trade
    Given orders data
      | user | type | price | quantity |
      | john | ask | 110 | 100 |
      | mary | bid | 100 | 100 |
    Then limit order book has "0" orders

  @fake_server
  Scenario: Full trade
    Given orders data
      | user | type | price | quantity |
      | john | ask | 110 | 200 |
      | mary | bid | 100 | 100 |
      | tom | bid | 105 | 100 |
    Then limit order book has "0" orders

  @fake_server
  Scenario: Full trade
    Given orders data
      | user | type | price | quantity |
      | john | ask | 110 | 100 |
      | mary | bid | 100 | 100 |
    Then limit order book has "0" orders

  @fake_server
  Scenario: Full trade
    Given orders data
      | user | type | price | quantity |
      | john | bid | 100 | 100 |
      | mary | ask | 100 | 100 |
    Then limit order book has "0" orders

  @fake_server
  Scenario: No trade
    Given orders data
      | user | type | price | quantity |
      | john | ask | 100 | 100 |
      | mary | bid | 120 | 100 |
    Then limit order book has "2" orders

  @fake_server
  Scenario: No trade
    Given orders data
      | user | type | price | quantity |
      | john | bid | 120 | 100 |
      | mary | ask | 119 | 100 |
    Then limit order book has "2" orders

  @fake_server
  Scenario: Partial trade
    Given orders data
      | user | type | price | quantity |
      | john | ask | 100 | 50 |
      | mary | bid | 100 | 100 |
    Then limit order book has "1" orders
    And "mary"'s order quantity is "50"

  @fake_server
  Scenario: Partial trade
    Given orders data
      | user | type | price | quantity |
      | john | bid | 100 | 100 |
      | mary | ask | 101 | 50 |
      | tom | ask | 120 | 100 |
    Then limit order book has "1" orders
    And "tom"'s order quantity is "50"

  @fake_server
  Scenario: Match decimal values
    Given orders data
      | user | type | price | quantity |
      | john | bid | 100.25 | 100 |
      | mary | ask | 100.43 | 100 |
    Then limit order book has "0" orders