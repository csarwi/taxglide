import React from 'react';
import TauriTest from '../TauriTest';
import CliTester from '../CliTester';
import { createCardStyle } from '../theme';

const Debug: React.FC = () => {
  return (
    <div>
      <div style={createCardStyle()}>
        <TauriTest />
      </div>
      
      <div style={{ marginTop: '24px', ...createCardStyle() }}>
        <CliTester />
      </div>
    </div>
  );
};

export default Debug;
