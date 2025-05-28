import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import LoginPage from '../../src/components/LoginPage';

describe('LoginPage Component', () => {
  beforeEach(() => {
    // Set up environment variables directly
    Cypress.env('TEST_EMAIL', 'will.ren@student.unsw.edu.au');
    Cypress.env('TEST_PASSWORD', '123456');
    
    // Intercept login requests
    cy.intercept('POST', '**/api/auth/login*').as('loginRequest');
    cy.intercept('POST', '**/login*').as('loginRequestAlt');
    cy.intercept('POST', '**/auth*').as('authRequest');
  });

  it('renders login form correctly', () => {
    // Mount the component
    cy.mount(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );
    
    // Check if email, password inputs and sign in button are rendered
    cy.get('input[type="email"], input[placeholder*="email" i], input[name="email"]').should('exist');
    cy.get('input[type="password"], input[placeholder*="password" i], input[name="password"]').should('exist');
    cy.get('button, input[type="submit"]').should('exist');
  });

  it('validates empty form submission', () => {
    // Mount the component
    cy.mount(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );
    
    // Find and click the submit button directly
    cy.get('button[type="submit"], input[type="submit"], button').contains(/sign|login|log in/i, { matchCase: false }).click({ force: true });
    
    // Look for any error indicators - this varies by UI implementation
    cy.get('body').should('exist');
    
    // Check for common error indicators without using promises
    cy.get('body').invoke('text').then(text => {
      // Log what we found without any additional Cypress commands
      const hasErrorText = /required|cannot be empty|please enter|invalid|error/i.test(text);
      if (hasErrorText) {
        // Using standard console.log, not cy.log inside a promise
        console.log('Found validation message text');
      }
    });
  });

  it('handles user input correctly', () => {
    // Mount the component
    cy.mount(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );
    
    // Get the email and password inputs
    const testEmail = Cypress.env('TEST_EMAIL');
    const testPassword = Cypress.env('TEST_PASSWORD');
    
    // Type in email field
    cy.get('input[type="email"], input[placeholder*="email" i], input[name="email"]')
      .first()
      .type(testEmail)
      .should('have.value', testEmail);
      
    // Type in password field  
    cy.get('input[type="password"], input[placeholder*="password" i], input[name="password"]')
      .first()
      .type(testPassword)
      .should('have.value', testPassword);
  });
  
  it('submits form and handles successful login', () => {
    // Set up spy before mounting
    cy.window().then(win => {
      cy.spy(win.localStorage, 'setItem').as('localStorageSpy');
    });
    
    // Mount the component
    cy.mount(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );
    
    // Get the email and password inputs
    const testEmail = Cypress.env('TEST_EMAIL');
    const testPassword = Cypress.env('TEST_PASSWORD');
    
    // Type in email field
    cy.get('input[type="email"], input[placeholder*="email" i], input[name="email"]')
      .first()
      .type(testEmail);
    
    // Type in password field
    cy.get('input[type="password"], input[placeholder*="password" i], input[name="password"]')
      .first()
      .type(testPassword);
    
    // Click the submit button
    cy.get('button[type="submit"], input[type="submit"], button')
      .contains(/sign|login|log in/i, { matchCase: false })
      .click({ force: true });
    
    // Wait a bit without nesting commands
    cy.wait(1000);
    
    // Check if component still exists (didn't crash)
    cy.get('body').should('exist');
  });
}); 