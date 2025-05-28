describe('Login Page', () => {
  beforeEach(() => {
    // Visit the root path where the login page is rendered
    cy.visit('/');
    
    // Add a longer timeout to ensure page loads
    cy.wait(2000);
  });

  it('debug - check page structure', () => {
    // Log the entire body HTML to console
    cy.get('body').then(($body) => {
      console.log('Body HTML:', $body.html());
    });

    // Try finding inputs by type instead of placeholder
    cy.get('input').then(($inputs) => {
      console.log('All inputs found:', $inputs.length);
      $inputs.each((index, input) => {
        console.log(`Input ${index}:`, input.type, input.placeholder);
      });
    });
    
    // Try finding buttons
    cy.get('button').then(($buttons) => {
      console.log('Buttons found:', $buttons.length);
      $buttons.each((index, button) => {
        console.log(`Button ${index} text:`, button.textContent);
      });
    });
  });

  it('displays the login form', () => {
    // Check that login form elements are visible
    cy.get('input').should('exist');
    cy.get('button').should('exist');
  });

  it('shows validation error for empty email', () => {
    // Try to submit without entering email
    cy.get('button').first().click();
    // Check for validation error (any error message)
    cy.contains(/error|required|invalid|please/i).should('exist');
  });

  it('shows validation error for empty password', () => {
    // Enter email but no password
    cy.get('input').first().type('test@example.com');
    cy.get('button').first().click();
    // Check for validation error (any error message)
    cy.contains(/error|required|invalid|please/i).should('exist');
  });

  it('navigates to signup page when clicking signup link', () => {
    // Find and click the signup link - try different selectors
    cy.contains(/sign up|register|create account/i).click();
    // URL should change to signup page
    cy.url().should('include', '/signup');
  });

  it('successfully logs in with valid credentials', () => {
    // Intercept API requests - update endpoint pattern if needed
    cy.intercept('POST', '**/api/**').as('loginRequest');

    // Enter valid credentials
    cy.get('input').first().type('will.ren@student.unsw.edu.au');
    cy.get('input[type="password"]').type('123456');
    cy.get('button').first().click();

    // Wait for the request to complete
    cy.wait('@loginRequest', { timeout: 10000 });
    
    // Should be redirected to a protected page
    cy.url().should('not.include', '/login');
  });
}); 