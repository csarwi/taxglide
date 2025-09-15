import React from 'react';
import TauriTest from '../TauriTest';
import { createCardStyle } from '../theme';

const Debug: React.FC = () => {
  return (
    <div>
      <div style={createCardStyle()}>
        <TauriTest />
      </div>
    </div>
  );
};

export default Debug;
