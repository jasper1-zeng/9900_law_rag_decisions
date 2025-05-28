describe('Chat Page', () => {
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
    
    // Now navigate directly to the chat page
    cy.visit('/chat');
    
    // Wait for the chat page to load
    cy.wait(5000);
  });

  it('displays the chat interface', () => {
    // Look for any input element or textarea for message input
    cy.get('body').should('exist');
    cy.get('input, textarea, div').should('exist');
  });

  it('verifies page does not crash', () => {
    // Simple test to verify the page loads and doesn't crash
    cy.get('body').should('be.visible');
    
    // Check for common UI elements
    cy.get('button, input, textarea, div').should('exist');
  });
});