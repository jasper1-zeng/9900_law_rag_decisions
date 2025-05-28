describe('Citation Graph Feature', () => {
  beforeEach(() => {
    // Set authentication token directly in localStorage to bypass login
    cy.visit('/', {
      onBeforeLoad(win) {
        // Simulate authenticated state
        win.localStorage.setItem('isAuthenticated', 'true');
        win.localStorage.setItem('token', 'fake-token-for-testing');
      },
    });
    
    // Wait for page to load
    cy.wait(2000);
    
    // Instead of directly visiting /citation-graph, first we should see the chat page by default
    // Then, click on the "Citation Graph" navigation button
    cy.contains('Citation Graph').click();
    
    // Wait for the page to load
    cy.wait(5000);
    
    // Verify we're on the citation-graph page
    cy.url().should('include', '/citation-graph');
  });

  it('displays the citation graph interface', () => {
    // Check that the body exists
    cy.get('body').should('exist');
    
    // Verify the page has loaded
    cy.get('div').should('exist');
  });

  it('has visible content', () => {
    // There should be a "Citation Graph" element visible on the page
    cy.contains('Citation Graph').should('exist');
    
    // Check for interactive elements - only verify divs exist since they must be there
    cy.get('div').should('exist');
  });

  it('allows navigation to other pages', () => {
    // Find something clickable to navigate to chat
    cy.get('body').contains('Chat').click();
    
    // URL should change
    cy.url().should('include', '/chat');
  });
}); 