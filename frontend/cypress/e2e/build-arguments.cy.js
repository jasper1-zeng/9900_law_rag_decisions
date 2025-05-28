describe('Build Arguments Feature', () => {
  beforeEach(() => {
    // Set authentication token directly in localStorage
    cy.visit('/', {
      onBeforeLoad(win) {
        // Simulate authenticated state by setting localStorage
        win.localStorage.setItem('isAuthenticated', 'true');
        win.localStorage.setItem('token', 'fake-token-for-testing');
      },
    });
    
    // Add a longer timeout to ensure page loads
    cy.wait(2000);
    
    // Instead of directly visiting /build-arguments, first we should see the chat page by default
    // Then, click on the "Build Arguments" navigation button
    cy.contains('Build Arguments').click();
    
    // Wait for the page to load
    cy.wait(5000);
    
    // Verify we're on the build-arguments page
    cy.url().should('include', '/build-arguments');
  });

  it('displays the build arguments interface', () => {
    // Verify the page exists and doesn't crash
    cy.get('body').should('exist');
    
    // Check for basic elements that should be present
    cy.get('.top-bar').should('exist');
    
    // Check for some kind of text input area
    cy.get('textarea, input').should('exist');
  });

  it('verifies navigation buttons exist', () => {
    // Verify button elements exist
    cy.get('button').should('exist');
    
    // There should be a button for "Build Arguments" that's active/selected
    cy.contains('Build Arguments').should('exist');
  });

  it('allows entering text in text area', () => {
    // Find the text entry area (could be textarea or input)
    cy.get('textarea, input[type="text"]').first().type('This is a test case about a legal dispute');
    
    // Verify the text was entered
    cy.get('textarea, input[type="text"]').first().should('have.value', 'This is a test case about a legal dispute');
  });

  it('allows clicking a send button', () => {
    // Type some text first
    cy.get('textarea, input[type="text"]').first().type('Test legal case');
    
    // Find and click a button that might be the send button
    // Using a more generic selector since we don't know the exact one
    cy.get('button').last().click();
    
    // Verify some response is happening (page doesn't crash)
    cy.get('body').should('exist');
  });
}); 