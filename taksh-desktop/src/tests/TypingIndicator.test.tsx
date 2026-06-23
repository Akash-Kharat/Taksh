import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './helpers';
import { TypingIndicator } from '../components/TypingIndicator';

describe('TypingIndicator Component', () => {
  it('renders correctly for THINKING stage', () => {
    renderWithProviders(<TypingIndicator stage="THINKING" />);
    expect(screen.getByText('Taksh is thinking...')).toBeTruthy();
  });

  it('renders correctly for RETRIEVING_MEMORY stage', () => {
    renderWithProviders(<TypingIndicator stage="RETRIEVING_MEMORY" />);
    expect(screen.getByText('Retrieving episodic memory...')).toBeTruthy();
  });

  it('renders correctly for SEARCHING_KNOWLEDGE stage', () => {
    renderWithProviders(<TypingIndicator stage="SEARCHING_KNOWLEDGE" />);
    expect(screen.getByText('Searching knowledge base...')).toBeTruthy();
  });

  it('renders correctly for GENERATING_RESPONSE stage', () => {
    renderWithProviders(<TypingIndicator stage="GENERATING_RESPONSE" />);
    expect(screen.getByText('Generating response...')).toBeTruthy();
  });
});
