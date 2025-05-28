import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import App from './App';

// Mock components to prevent full rendering of each page
jest.mock('./components/SearchPage', () => () => <div>SearchPage</div>);
jest.mock('./components/ChatPage', () => () => <div>ChatPage</div>);
jest.mock('./components/loginPage', () => () => <div>LoginPage</div>);

test('renders app with router', () => {
  render(
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
  
  // Verify App renders without crashing
  expect(document.querySelector('.App')).toBeInTheDocument();
});

test('renders routes correctly', () => {
  // This is a basic test to ensure App renders with Router
  // More specific route testing would be done with router testing
  const { container } = render(
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
  
  expect(container).toBeInTheDocument();
});
