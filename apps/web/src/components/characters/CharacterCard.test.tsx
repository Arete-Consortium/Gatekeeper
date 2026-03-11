import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CharacterCard } from './CharacterCard';
import type { LinkedCharacter } from '@/lib/types';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  MapPin: (props: Record<string, unknown>) => <span data-testid="map-pin-icon" {...props} />,
  Ship: (props: Record<string, unknown>) => <span data-testid="ship-icon" {...props} />,
  Star: (props: Record<string, unknown>) => <span data-testid="star-icon" {...props} />,
  Trash2: (props: Record<string, unknown>) => <span data-testid="trash-icon" {...props} />,
  CheckCircle: (props: Record<string, unknown>) => <span data-testid="check-circle-icon" {...props} />,
}));

function makeCharacter(overrides: Partial<LinkedCharacter> = {}): LinkedCharacter {
  return {
    character_id: 12345,
    character_name: 'Test Pilot',
    is_active: true,
    preferences: null,
    location: null,
    ...overrides,
  };
}

const defaultProps = {
  isActiveCharacter: false,
  onSetActive: vi.fn(),
  onRemove: vi.fn(),
};

describe('CharacterCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders character name', () => {
    render(
      <CharacterCard character={makeCharacter()} {...defaultProps} />
    );
    expect(screen.getByText('Test Pilot')).toBeInTheDocument();
  });

  it('renders character ID', () => {
    render(
      <CharacterCard character={makeCharacter()} {...defaultProps} />
    );
    expect(screen.getByText('ID: 12345')).toBeInTheDocument();
  });

  it('renders portrait with correct URL', () => {
    render(
      <CharacterCard character={makeCharacter()} {...defaultProps} />
    );
    const img = screen.getByAltText('Test Pilot portrait') as HTMLImageElement;
    expect(img.src).toContain('https://images.evetech.net/characters/12345/portrait?size=128');
  });

  it('shows active indicator when isActiveCharacter is true', () => {
    render(
      <CharacterCard
        character={makeCharacter()}
        {...defaultProps}
        isActiveCharacter={true}
      />
    );
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('does not show active indicator when isActiveCharacter is false', () => {
    render(
      <CharacterCard character={makeCharacter()} {...defaultProps} />
    );
    expect(screen.queryByText('Active')).not.toBeInTheDocument();
  });

  it('shows Set Active button when not active character', () => {
    render(
      <CharacterCard character={makeCharacter()} {...defaultProps} />
    );
    expect(screen.getByText('Set Active')).toBeInTheDocument();
  });

  it('hides Set Active button when active character', () => {
    render(
      <CharacterCard
        character={makeCharacter()}
        {...defaultProps}
        isActiveCharacter={true}
      />
    );
    expect(screen.queryByText('Set Active')).not.toBeInTheDocument();
  });

  it('calls onSetActive when Set Active button is clicked', async () => {
    const onSetActive = vi.fn();
    const user = userEvent.setup();
    render(
      <CharacterCard
        character={makeCharacter()}
        {...defaultProps}
        onSetActive={onSetActive}
      />
    );
    await user.click(screen.getByText('Set Active'));
    expect(onSetActive).toHaveBeenCalledWith(12345);
  });

  it('shows Remove button', () => {
    render(
      <CharacterCard character={makeCharacter()} {...defaultProps} />
    );
    expect(screen.getByText('Remove')).toBeInTheDocument();
  });

  it('shows confirmation on first Remove click', async () => {
    const user = userEvent.setup();
    render(
      <CharacterCard character={makeCharacter()} {...defaultProps} />
    );
    await user.click(screen.getByText('Remove'));
    expect(screen.getByText('Confirm Remove')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('calls onRemove on confirm click', async () => {
    const onRemove = vi.fn();
    const user = userEvent.setup();
    render(
      <CharacterCard
        character={makeCharacter()}
        {...defaultProps}
        onRemove={onRemove}
      />
    );
    await user.click(screen.getByText('Remove'));
    await user.click(screen.getByText('Confirm Remove'));
    expect(onRemove).toHaveBeenCalledWith(12345);
  });

  it('cancels removal on Cancel click', async () => {
    const onRemove = vi.fn();
    const user = userEvent.setup();
    render(
      <CharacterCard
        character={makeCharacter()}
        {...defaultProps}
        onRemove={onRemove}
      />
    );
    await user.click(screen.getByText('Remove'));
    await user.click(screen.getByText('Cancel'));
    expect(onRemove).not.toHaveBeenCalled();
    expect(screen.getByText('Remove')).toBeInTheDocument();
  });

  it('renders location when available', () => {
    const character = makeCharacter({
      location: {
        solar_system_id: 30000142,
        solar_system_name: 'Jita',
        security: 0.95,
        region_name: 'The Forge',
        station_id: null,
        structure_id: null,
      },
    });
    render(
      <CharacterCard character={character} {...defaultProps} />
    );
    expect(screen.getByText('Jita')).toBeInTheDocument();
    expect(screen.getByText('(The Forge)')).toBeInTheDocument();
  });

  it('shows Authenticated text for active tokens', () => {
    render(
      <CharacterCard character={makeCharacter({ is_active: true })} {...defaultProps} />
    );
    expect(screen.getByText('Authenticated')).toBeInTheDocument();
  });

  it('shows Token expired for expired tokens', () => {
    render(
      <CharacterCard character={makeCharacter({ is_active: false })} {...defaultProps} />
    );
    expect(screen.getByText('Token expired')).toBeInTheDocument();
  });

  it('disables Set Active button when token is expired', () => {
    render(
      <CharacterCard
        character={makeCharacter({ is_active: false })}
        {...defaultProps}
      />
    );
    const setActiveBtn = screen.getByText('Set Active').closest('button');
    expect(setActiveBtn).toBeDisabled();
  });

  it('applies ring styling when active', () => {
    const { container } = render(
      <CharacterCard
        character={makeCharacter()}
        {...defaultProps}
        isActiveCharacter={true}
      />
    );
    const card = container.querySelector('[data-testid="character-card-12345"]');
    expect(card).toHaveClass('ring-2');
  });
});
