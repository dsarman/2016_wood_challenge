Feature: Process incoming client messages and respond accordingly if needed to

  @real_server
  @fake_client
  @logged_in
  Scenario: Message to create new order is received
    When message with order data is received
    Then order is created
    And client receives the "1" created orders ids


  @real_server
  @fake_client
  @logged_in
  Scenario: Multiple new orders received
    When message with order data is received
    And message with order data is received
    And message with order data is received
    Then client receives the "3" created orders ids

  # Currently sporadically fails due to bug in server shutdown method.
  # @real_server
  # @fake_client
  # @logged_in
  # Scenario: Deletion of existing order
  #   When order already exists
  #   And message to delete order is received
  #   Then order is deleted